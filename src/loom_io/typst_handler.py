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

from ..core.types import Lines
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

# Import shared template utilities
from .template_io import (
    TemplateDescriptor,
    TemplateSectionRule,
    FrozenRules,
    find_template_descriptor_path,
    load_descriptor,
    detect_inline_marker as _detect_inline_marker,
)

# Typst-specific inline marker pattern (// or /* loom-template: <id>)
_INLINE_MARKER_RE = re.compile(
    r"(?://|/\*)\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)", re.IGNORECASE
)
_MARKER_SEARCH_LINES = 30


@dataclass
class TypstSection:
    key: str
    heading_text: str
    start_line: int
    end_line: int
    confidence: float
    items: list[int] = field(default_factory=list)
    source: str = "generic"


@dataclass
class TypstAnalysis:
    sections: list[TypstSection]
    normalized_order: list[str]
    notes: list[str]
    descriptor: TemplateDescriptor | None
    frozen_ranges: list[Tuple[int, int]]
    header_lines: list[int]


# * Detect inline marker in Typst file (uses Typst-specific // or /* comment pattern)
# parse inline marker from Typst file using // or /* comment syntax
def detect_inline_marker(text: str) -> str | None:
    return _detect_inline_marker(
        text, _INLINE_MARKER_RE, max_lines=_MARKER_SEARCH_LINES
    )


# * Detect template for a Typst file
def detect_template(resume_path: Path, content: str) -> TemplateDescriptor | None:
    inline_marker = detect_inline_marker(content)
    descriptor_path = find_template_descriptor_path(resume_path)

    if descriptor_path:
        return load_descriptor(descriptor_path, inline_marker)

    # Fallback: create minimal descriptor from inline marker if present
    if inline_marker:
        return TemplateDescriptor(
            id=inline_marker,
            name=inline_marker,
            type="resume",
            version=None,
            sections={},
            frozen=FrozenRules(),
            custom={},
            inline_marker=inline_marker,
            inline_only=True,
        )

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
    heading_lines: list[Tuple[int, int, str]] = []
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
                i += 2
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


# * Run `typst compile` if available
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


# * Check availability of Typst compiler
def check_typst_availability() -> Dict[str, bool]:
    result = {"typst": False}
    try:
        subprocess.run(
            ["typst", "--version"],
            capture_output=True,
            timeout=5,
        )
        result["typst"] = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return result


# * Validate Typst document w/ optional compilation check
def validate_typst_document(
    content: str, check_compilation: bool = True
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "syntax_valid": False,
        "compilation_checked": False,
        "compilation_success": False,
        "errors": [],
        "warnings": [],
    }

    # Check basic syntax first
    if validate_basic_typst_syntax(content):
        result["syntax_valid"] = True
    else:
        result["errors"].append(
            "Typst syntax validation failed (unbalanced delimiters or unterminated string)"
        )
        return result

    # Optionally check compilation
    if check_compilation:
        availability = check_typst_availability()
        if availability["typst"]:
            try:
                success, message = validate_typst_compilation(content)
                result["compilation_checked"] = True
                result["compilation_success"] = success
                if not success:
                    result["errors"].append(message)
            except Exception as e:
                result["errors"].append(f"Compilation validation error: {e}")
        else:
            result["warnings"].append(
                "Typst compiler not available; skipping compilation check"
            )

    return result


# === Handler Class (OO API) ===

from typing import Pattern
from .base_handler import BaseDocumentHandler
from .types import DocumentSection, DocumentAnalysis


# handler for Typst (.typ) resume documents w/ OO interface for template detection, analysis & filtering
class TypstHandler(BaseDocumentHandler):
    format_type = "typst"

    @property
    def inline_marker_pattern(self) -> Pattern[str]:
        return _INLINE_MARKER_RE

    @property
    def inline_marker_max_lines(self) -> int | None:
        return _MARKER_SEARCH_LINES

    @property
    def semantic_matchers(self) -> dict[str, Pattern[str]]:
        return SEMANTIC_MATCHERS

    # analyze Typst document structure & extract sections
    def analyze(
        self, lines: Lines, descriptor: TemplateDescriptor | None = None
    ) -> DocumentAnalysis:
        # use existing analyze_typst function
        legacy_analysis = analyze_typst(lines, descriptor)

        # Convert to unified DocumentSection/DocumentAnalysis types
        sections = [
            DocumentSection(
                key=s.key,
                heading_text=s.heading_text,
                start_line=s.start_line,
                end_line=s.end_line,
                confidence=s.confidence,
                items=s.items,
                source=s.source,
                kind=s.key,  # kind same as key for Typst
            )
            for s in legacy_analysis.sections
        ]

        return DocumentAnalysis(
            sections=sections,
            normalized_order=legacy_analysis.normalized_order,
            notes=legacy_analysis.notes,
            descriptor=legacy_analysis.descriptor,
            format_type="typst",
            frozen_ranges=legacy_analysis.frozen_ranges,
            header_lines=legacy_analysis.header_lines,
        )

    # check if line is structural & should not be edited
    def is_structural_line(
        self, line: str, frozen_patterns: list[str] | None = None
    ) -> bool:
        return is_structural_line(line, frozen_patterns=frozen_patterns)

    # check if line is in a frozen range (returns True if OK to edit, False if frozen)
    def _check_frozen_ranges(self, line_num: int, kwargs: dict) -> bool:
        frozen_ranges = kwargs.get("frozen_ranges")
        if frozen_ranges is not None:
            return not is_in_frozen_range(line_num, frozen_ranges)
        return True

    # Typst-specific edit validation (simpler than LaTeX - no command preservation rules)
    def _validate_edit(
        self, op: dict, lines: Lines, affected_lines: list[int], notes: list[str]
    ) -> bool:
        # currently no Typst-specific validation beyond structural checks
        return True

    # validate basic Typst syntax
    def validate_syntax(self, content: str) -> bool:
        return validate_basic_typst_syntax(content)

    # attempt Typst compilation & return result
    def validate_compilation(self, content: str) -> Dict[str, Any]:
        success, message = validate_typst_compilation(content)
        return {
            "success": success,
            "errors": [] if success else [message],
            "warnings": [],
        }

    # check if Typst compiler is available
    def check_tool_availability(self) -> Dict[str, bool]:
        return check_typst_availability()

    # Override sections_to_payload to match legacy format
    # convert analysis to JSON-serializable payload for AI
    def sections_to_payload(self, analysis: DocumentAnalysis) -> dict:
        sections_data = []
        for s in analysis.sections:
            sections_data.append(
                {
                    "kind": s.kind or s.key,
                    "heading_text": s.heading_text,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "items": s.items if s.items else [],
                }
            )

        return {
            "sections": sections_data,
            "section_order": analysis.normalized_order,
            "notes": analysis.notes,
            "template_id": analysis.descriptor.id if analysis.descriptor else None,
        }

    # Override filter_edits to use legacy implementation for full feature parity
    def filter_edits(
        self,
        edits: dict,
        lines: Lines,
        descriptor: TemplateDescriptor | None = None,
        **kwargs,
    ) -> Tuple[dict, list[str]]:
        # filter edits to protect structural content
        frozen_ranges = kwargs.get("frozen_ranges")
        return filter_typst_edits(edits, lines, descriptor, frozen_ranges)

    # Typst-specific: expose frozen range detection for multi-line structural blocks
    def find_frozen_ranges(self, lines: Lines) -> list[Tuple[int, int]]:
        return find_frozen_ranges(lines)

    # convenience method matching legacy build_typst_context signature
    def build_context(
        self, resume_path: Path, lines: Lines, text: str
    ) -> Tuple[TemplateDescriptor | None, DocumentAnalysis]:
        descriptor = self.detect_template(resume_path, text)
        analysis = self.analyze(lines, descriptor)
        return descriptor, analysis


__all__ = [
    # Handler class (public API)
    "TypstHandler",
    # Frozen range utilities (useful for external callers)
    "find_frozen_ranges",
    "is_in_frozen_range",
    # Validation utilities (standalone, may be useful externally)
    "validate_basic_typst_syntax",
    "validate_typst_compilation",
    "check_typst_availability",
    "validate_typst_document",
]
