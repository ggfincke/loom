# src/loom_io/typst_handler.py
# Typst handler w/ section detection, template metadata, frozen block tracking & edit filtering

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple
import re
import shutil
import subprocess
import tempfile
import tomllib

from .types import Lines
from .typst_patterns import (
    STRUCTURAL_PREFIXES,
    SECTION_HEADING_RE,
    ENTRY_FUNC_PATTERNS,
    SEMANTIC_MATCHERS,
    is_structural_line,
    is_section_heading,
    is_entry_function,
    is_bullet_line,
    count_delimiters,
    infer_section_kind,
)

# Reuse template descriptor types from latex_handler
from .latex_handler import TemplateDescriptor, TemplateSectionRule, FrozenRules

# Template detection constants
_TEMPLATE_FILENAME = "loom-template.toml"
_INLINE_MARKER_RE = re.compile(
    r"(?://|/\*)\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)", re.IGNORECASE
)
_MARKER_SEARCH_LINES = 30  # Only search first N lines


@dataclass
class TypstSection:
    key: str  # Normalized kind (e.g., "experience")
    heading_text: str  # Original heading text
    start_line: int
    end_line: int
    confidence: float
    items: list[int] = field(default_factory=list)  # Line numbers of entry functions
    source: str = "generic"  # "template", "generic", "semantic", "fallback"


@dataclass
class TypstAnalysis:
    sections: list[TypstSection]
    normalized_order: list[str]
    notes: list[str]
    descriptor: TemplateDescriptor | None
    frozen_ranges: list[Tuple[int, int]]  # (start_line, end_line) of frozen blocks
    header_lines: list[int]  # Lines before first section heading


# * Find loom-template.toml by walking up from resume path
def find_template_descriptor_path(resume_path: Path) -> Path | None:
    current = resume_path.resolve().parent
    for parent in [current] + list(current.parents):
        candidate = parent / _TEMPLATE_FILENAME
        if candidate.exists():
            return candidate
    return None


# * Detect inline marker in Typst file (first N lines)
def detect_inline_marker(text: str) -> str | None:
    lines = text.split("\n")[:_MARKER_SEARCH_LINES]
    for line in lines:
        match = _INLINE_MARKER_RE.search(line)
        if match:
            return match.group("id").strip()
    return None


# * Load template descriptor from path
def load_descriptor(
    descriptor_path: Path, inline_marker: str | None = None
) -> TemplateDescriptor:
    with open(descriptor_path, "rb") as f:
        data = tomllib.load(f)

    template = data.get("template", {})
    sections_raw = data.get("sections", {})
    frozen_raw = data.get("frozen", {})
    custom = data.get("custom", {})

    sections: dict[str, TemplateSectionRule] = {}
    for key, sec_data in sections_raw.items():
        sections[key] = TemplateSectionRule(
            key=key,
            pattern=sec_data.get("pattern", ""),
            pattern_type=sec_data.get("pattern_type", "literal"),
            kind=sec_data.get("kind"),
            split_items=sec_data.get("split_items", False),
            optional=sec_data.get("optional", True),
        )

    frozen_paths = [Path(p) for p in frozen_raw.get("paths", [])]
    frozen_patterns = frozen_raw.get("patterns", [])

    return TemplateDescriptor(
        id=template.get("id", "unknown"),
        type=template.get("type", "resume"),
        name=template.get("name"),
        version=template.get("version"),
        sections=sections,
        frozen=FrozenRules(paths=frozen_paths, patterns=frozen_patterns),
        custom=custom,
        source_path=descriptor_path,
        inline_marker=inline_marker,
    )


# * Detect template for a Typst file
def detect_template(resume_path: Path, content: str) -> TemplateDescriptor | None:
    inline_marker = detect_inline_marker(content)
    descriptor_path = find_template_descriptor_path(resume_path)

    if descriptor_path:
        return load_descriptor(descriptor_path, inline_marker)
    return None


# * Find line ranges for multi-line structural blocks
def find_frozen_ranges(lines: Lines) -> list[Tuple[int, int]]:
    frozen_ranges: list[Tuple[int, int]] = []
    in_block = False
    block_start = 0
    paren_depth = 0

    for line_num in sorted(lines.keys()):
        text = lines[line_num]
        stripped = text.strip()

        # Check if line starts a structural block
        if not in_block:
            if stripped.startswith(STRUCTURAL_PREFIXES):
                in_block = True
                block_start = line_num
                paren_depth = count_delimiters(text)
                # If balanced on same line, close immediately
                if paren_depth <= 0:
                    frozen_ranges.append((block_start, line_num))
                    in_block = False
                    paren_depth = 0
        else:
            # Continue tracking until balanced
            paren_depth += count_delimiters(text)
            if paren_depth <= 0:
                frozen_ranges.append((block_start, line_num))
                in_block = False
                paren_depth = 0

    # Handle unclosed block (shouldn't happen in valid Typst)
    if in_block:
        frozen_ranges.append((block_start, max(lines.keys())))

    return frozen_ranges


# * Check if a line number falls within any frozen range
def is_in_frozen_range(
    line_num: int, frozen_ranges: list[Tuple[int, int]] | None
) -> bool:
    if not frozen_ranges:
        return False
    return any(start <= line_num <= end for start, end in frozen_ranges)


# * Detect section boundaries using template patterns or generic heading detection
def _detect_sections(
    lines: Lines, descriptor: TemplateDescriptor | None
) -> list[TypstSection]:
    sections: list[TypstSection] = []
    sorted_line_nums = sorted(lines.keys())

    if not sorted_line_nums:
        return sections

    # Find all section headings
    heading_lines: list[Tuple[int, int, str]] = []  # (line_num, level, title)
    for line_num in sorted_line_nums:
        result = is_section_heading(lines[line_num])
        if result:
            level, title = result
            heading_lines.append((line_num, level, title))

    if not heading_lines:
        # Fallback: treat entire document as single section
        return [
            TypstSection(
                key="content",
                heading_text="",
                start_line=sorted_line_nums[0],
                end_line=sorted_line_nums[-1],
                confidence=0.4,
                items=[],
                source="fallback",
            )
        ]

    # Build sections from headings
    for i, (line_num, level, title) in enumerate(heading_lines):
        # Determine end line (start of next heading or end of doc)
        if i + 1 < len(heading_lines):
            end_line = heading_lines[i + 1][0] - 1
        else:
            end_line = sorted_line_nums[-1]

        # Infer section kind from title
        kind = infer_section_kind(title)
        if kind is None:
            # Normalize title to key
            kind = title.lower().replace(" ", "_")

        # Check if template descriptor has a rule for this section
        source = "generic"
        confidence = 0.72
        if descriptor:
            for rule_key, rule in descriptor.sections.items():
                if rule.pattern_type == "regex":
                    if re.search(rule.pattern, lines[line_num]):
                        kind = rule.kind or rule_key
                        source = "template"
                        confidence = 0.88
                        break
                elif rule.pattern in lines[line_num]:
                    kind = rule.kind or rule_key
                    source = "template"
                    confidence = 0.88
                    break

        sections.append(
            TypstSection(
                key=kind,
                heading_text=title,
                start_line=line_num,
                end_line=end_line,
                confidence=confidence,
                items=[],
                source=source,
            )
        )

    return sections


# * Detect entry function boundaries within a section
def detect_item_boundaries(lines: Lines, start: int, end: int) -> list[int]:
    boundaries: list[int] = []
    for line_num in range(start, end + 1):
        if line_num in lines and is_entry_function(lines[line_num]):
            boundaries.append(line_num)
    return boundaries


# * Analyze Typst document structure
def analyze_typst(lines: Lines, descriptor: TemplateDescriptor | None) -> TypstAnalysis:
    notes: list[str] = []
    sorted_line_nums = sorted(lines.keys())

    if not sorted_line_nums:
        return TypstAnalysis(
            sections=[],
            normalized_order=[],
            notes=["Empty document"],
            descriptor=descriptor,
            frozen_ranges=[],
            header_lines=[],
        )

    # Find frozen ranges (multi-line structural blocks)
    frozen_ranges = find_frozen_ranges(lines)
    if frozen_ranges:
        notes.append(f"Found {len(frozen_ranges)} frozen structural block(s)")

    # Detect sections
    sections = _detect_sections(lines, descriptor)

    # Find header lines (before first section)
    header_lines: list[int] = []
    if sections:
        first_section_start = sections[0].start_line
        header_lines = [ln for ln in sorted_line_nums if ln < first_section_start]

    # Detect item boundaries within sections that have split_items enabled
    for section in sections:
        should_split = False
        if descriptor and section.key in descriptor.sections:
            should_split = descriptor.sections[section.key].split_items

        if should_split:
            # Find entry function calls as item boundaries
            section.items = detect_item_boundaries(
                lines, section.start_line + 1, section.end_line
            )

    # Build normalized order
    normalized_order = [s.key for s in sections]

    return TypstAnalysis(
        sections=sections,
        normalized_order=normalized_order,
        notes=notes,
        descriptor=descriptor,
        frozen_ranges=frozen_ranges,
        header_lines=header_lines,
    )


# * Convert analysis to JSON-serializable payload for AI
def sections_to_payload(analysis: TypstAnalysis) -> dict:
    sections_data = []
    for s in analysis.sections:
        sections_data.append(
            {
                "kind": s.key,
                "heading_text": s.heading_text,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "items": s.items,
            }
        )

    return {
        "sections": sections_data,
        "section_order": analysis.normalized_order,
        "notes": analysis.notes,
        "template_id": analysis.descriptor.id if analysis.descriptor else None,
    }


# * Filter edits that would touch frozen lines/ranges
def filter_typst_edits(
    edits: dict,
    lines: Lines,
    descriptor: TemplateDescriptor | None,
    frozen_ranges: list[Tuple[int, int]] | None = None,
) -> Tuple[dict, list[str]]:
    notes: list[str] = []
    frozen_patterns = descriptor.frozen.patterns if descriptor else []

    # Compute frozen ranges if not provided
    if frozen_ranges is None:
        frozen_ranges = find_frozen_ranges(lines)

    ops = edits.get("ops", [])
    if not ops:
        return edits, notes

    filtered_ops: list[dict] = []

    for op in ops:
        op_type = op.get("op") or op.get("operation", "")
        line_num = op.get("line") or op.get("line_number")
        start_line = op.get("start") or op.get("start_line")
        end_line = op.get("end") or op.get("end_line")

        # Determine affected line range
        affected_lines: list[int] = []
        if line_num is not None:
            affected_lines = [line_num]
        if start_line is not None and end_line is not None:
            affected_lines = list(range(start_line, end_line + 1))

        # Check if any affected line is frozen
        skip = False
        for ln in affected_lines:
            # Check frozen ranges
            if is_in_frozen_range(ln, frozen_ranges):
                notes.append(f"Skipped {op_type} on frozen range line {ln}")
                skip = True
                break

            # Check structural line
            if ln in lines and is_structural_line(
                lines[ln], frozen_patterns=frozen_patterns
            ):
                notes.append(f"Skipped {op_type} on structural line {ln}")
                skip = True
                break

        if not skip:
            filtered_ops.append(op)

    result = {**edits, "ops": filtered_ops}
    return result, notes


# * Validate basic Typst syntax (balanced delimiters, no unterminated strings)
def validate_basic_typst_syntax(text: str) -> bool:
    # Track delimiter balance
    paren_count = 0
    bracket_count = 0
    brace_count = 0
    in_string = False
    in_line_comment = False
    in_block_comment = False

    i = 0
    while i < len(text):
        char = text[i]

        # Handle line comments
        if not in_string and not in_block_comment:
            if i + 1 < len(text) and text[i : i + 2] == "//":
                in_line_comment = True
                i += 2
                continue

        # Handle block comments
        if not in_string and not in_line_comment:
            if i + 1 < len(text) and text[i : i + 2] == "/*":
                in_block_comment = True
                i += 2
                continue
            if in_block_comment and i + 1 < len(text) and text[i : i + 2] == "*/":
                in_block_comment = False
                i += 2
                continue

        # Handle newline (ends line comment)
        if char == "\n":
            in_line_comment = False
            i += 1
            continue

        # Skip if in comment
        if in_line_comment or in_block_comment:
            i += 1
            continue

        # Handle strings
        if char == '"' and not in_string:
            in_string = True
            i += 1
            continue
        if in_string:
            if char == "\\" and i + 1 < len(text):
                i += 2  # Skip escaped char
                continue
            if char == '"':
                in_string = False
            i += 1
            continue

        # Count delimiters
        if char == "(":
            paren_count += 1
        elif char == ")":
            paren_count -= 1
        elif char == "[":
            bracket_count += 1
        elif char == "]":
            bracket_count -= 1
        elif char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1

        # Negative count means unmatched closing delimiter
        if paren_count < 0 or bracket_count < 0 or brace_count < 0:
            return False

        i += 1

    # Check for unterminated string
    if in_string:
        return False

    # Check for unterminated block comment
    if in_block_comment:
        return False

    # Check balanced delimiters
    if paren_count != 0 or bracket_count != 0 or brace_count != 0:
        return False

    return True


# * Optional: run `typst compile` if available
def validate_typst_compilation(content: str) -> Tuple[bool, str]:
    typst_path = shutil.which("typst")
    if not typst_path:
        return True, "typst CLI not found, skipping compilation check"

    # Must write to temp file - typst compile requires file path
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".typ", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        # Compile to a temp PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as pdf_out:
            result = subprocess.run(
                [typst_path, "compile", str(temp_path), pdf_out.name],
                capture_output=True,
                text=True,
                timeout=30,
            )

        if result.returncode == 0:
            return True, "compilation successful"
        return False, f"compilation failed: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return False, "compilation timed out"
    except Exception as e:
        return True, f"compilation check skipped: {e}"
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


# * Build context tuple for Typst document (similar to LaTeX)
def build_typst_context(
    resume_path: Path, lines: Lines, text: str
) -> Tuple[TemplateDescriptor | None, TypstAnalysis]:
    descriptor = detect_template(resume_path, text)
    analysis = analyze_typst(lines, descriptor)
    return descriptor, analysis


__all__ = [
    # Dataclasses
    "TypstSection",
    "TypstAnalysis",
    # Functions
    "find_template_descriptor_path",
    "detect_inline_marker",
    "load_descriptor",
    "detect_template",
    "find_frozen_ranges",
    "is_in_frozen_range",
    "detect_item_boundaries",
    "analyze_typst",
    "sections_to_payload",
    "filter_typst_edits",
    "validate_basic_typst_syntax",
    "validate_typst_compilation",
    "build_typst_context",
]
