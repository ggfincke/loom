# src/loom_io/latex_handler.py
# LaTeX handler w/ universal parsing, template metadata loading, & safe edit filtering

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple
import re
import subprocess
import tempfile
import tomllib

from .types import Lines
from .latex_patterns import (
    STRUCTURAL_PREFIXES,
    is_structural_line,
    SECTION_CMD_RE,
    SEMANTIC_MATCHERS,
    BULLET_PATTERNS,
)

# template descriptor constants
_TEMPLATE_FILENAME = "loom-template.toml"
_INLINE_TEMPLATE_RE = re.compile(r"%\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)")


@dataclass
class TemplateSectionRule:
    key: str
    pattern: str
    pattern_type: str = "literal"
    kind: str | None = None
    split_items: bool = False
    optional: bool = True


@dataclass
class FrozenRules:
    paths: list[Path] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)


@dataclass
class TemplateDescriptor:
    id: str
    type: str
    name: str | None
    version: str | None
    sections: dict[str, TemplateSectionRule]
    frozen: FrozenRules
    custom: Dict[str, Any]
    source_path: Path | None = None
    inline_marker: str | None = None
    inline_only: bool = False


@dataclass
class LatexSection:
    key: str
    heading_text: str
    start_line: int
    end_line: int
    confidence: float
    items: list[int] = field(default_factory=list)
    source: str = "generic"


@dataclass
class LatexAnalysis:
    sections: list[LatexSection]
    normalized_order: list[str]
    notes: list[str]
    descriptor: TemplateDescriptor | None
    preamble_lines: list[int]
    body_lines: list[int]


# * Find loom-template.toml by walking up from resume path
def find_template_descriptor_path(resume_path: Path) -> Path | None:
    current = resume_path.resolve().parent
    for parent in [current] + list(current.parents):
        candidate = parent / _TEMPLATE_FILENAME
        if candidate.exists():
            return candidate
    return None


# * Parse inline marker in LaTeX file
def detect_inline_marker(text: str) -> str | None:
    match = _INLINE_TEMPLATE_RE.search(text)
    if match:
        return match.group("id").strip()
    return None


# * Load template descriptor from path
def load_descriptor(
    descriptor_path: Path, inline_marker: str | None = None
) -> TemplateDescriptor:
    raw = tomllib.loads(descriptor_path.read_text(encoding="utf-8"))
    template_meta = raw.get("template", {})
    template_id = template_meta.get("id")
    template_type = template_meta.get("type")
    name = template_meta.get("name")
    version = template_meta.get("version")
    if template_id is None or template_type is None:
        raise ValueError(
            f"Template descriptor {descriptor_path} missing required template.id or template.type"
        )

    sections_raw = raw.get("sections", {})
    section_rules: dict[str, TemplateSectionRule] = {}
    for key, config in sections_raw.items():
        section_rules[key] = TemplateSectionRule(
            key=key,
            pattern=config.get("pattern", ""),
            pattern_type=config.get("pattern_type", "literal"),
            kind=config.get("kind"),
            split_items=bool(config.get("split_items", False)),
            optional=bool(config.get("optional", True)),
        )

    frozen_raw = raw.get("frozen", {})
    frozen_paths = [Path(p) for p in frozen_raw.get("paths", [])]
    frozen_patterns = frozen_raw.get("patterns", [])
    frozen_rules = FrozenRules(paths=frozen_paths, patterns=frozen_patterns or [])

    custom_meta = raw.get("custom", {})

    return TemplateDescriptor(
        id=template_id,
        type=template_type,
        name=name,
        version=version,
        sections=section_rules,
        frozen=frozen_rules,
        custom=custom_meta if isinstance(custom_meta, dict) else {},
        source_path=descriptor_path,
        inline_marker=inline_marker,
        inline_only=False,
    )


# * Detect template descriptor or inline marker near resume
def detect_template(
    resume_path: Path, content: str | None = None
) -> TemplateDescriptor | None:
    inline_marker = detect_inline_marker(content or "")
    descriptor_path = find_template_descriptor_path(resume_path)

    if descriptor_path:
        descriptor = load_descriptor(descriptor_path, inline_marker=inline_marker)
        return descriptor

    if inline_marker:
        # no descriptor file but marker present -> inline-only descriptor
        return TemplateDescriptor(
            id=inline_marker,
            type="resume",
            name=None,
            version=None,
            sections={},
            frozen=FrozenRules(),
            custom={},
            source_path=None,
            inline_marker=inline_marker,
            inline_only=True,
        )

    return None


# * Split LaTeX lines into preamble/body buckets based on \begin/\end{document}
def split_preamble_body(lines: Lines) -> tuple[list[int], list[int]]:
    preamble: list[int] = []
    body: list[int] = []
    seen_document = False
    ended_document = False

    for line_num, text in sorted(lines.items()):
        stripped = text.strip()
        if "\\end{document}" in stripped:
            ended_document = True
        if not seen_document:
            preamble.append(line_num)
        elif not ended_document:
            body.append(line_num)

        if "\\begin{document}" in stripped:
            seen_document = True

    # if no explicit document markers, treat all as body
    if not seen_document:
        preamble = []
        body = sorted(lines.keys())

    return preamble, body


# * Normalize heading text into canonical kind
def _infer_kind_from_heading(heading: str, fallback: str = "other") -> str:
    head_lower = heading.lower()
    for kind, matcher in SEMANTIC_MATCHERS.items():
        if matcher.search(head_lower):
            return kind
    return fallback


# * Build LatexSection boundaries from detected heading lines
def _finalize_sections(
    headings: list[tuple[int, str, str, str]], lines: Lines, body_lines: list[int]
) -> list[LatexSection]:
    sections: list[LatexSection] = []
    if not body_lines:
        return sections

    sorted_headings = sorted(headings, key=lambda h: h[0])
    section_ranges: list[tuple[int, int, str, str]] = []
    body_end = body_lines[-1]
    for idx, (start_line, heading_text, key, source) in enumerate(sorted_headings):
        if idx + 1 < len(sorted_headings):
            next_start = sorted_headings[idx + 1][0]
            end_line = next_start - 1
        else:
            end_line = body_end
        section_ranges.append((start_line, end_line, heading_text, source))

    for start_line, end_line, heading_text, source in section_ranges:
        kind = _infer_kind_from_heading(heading_text, fallback=key)
        sections.append(
            LatexSection(
                key=kind,
                heading_text=heading_text,
                start_line=start_line,
                end_line=end_line,
                confidence=0.88 if source == "template" else 0.72,
                source=source,
            )
        )
    return sections


# * Detect sections using template descriptor rules
def _detect_template_sections(
    lines: Lines, descriptor: TemplateDescriptor, body_lines: list[int]
) -> tuple[list[LatexSection], list[str]]:
    headings: list[tuple[int, str, str, str]] = []
    notes: list[str] = []
    for key, rule in descriptor.sections.items():
        pattern = rule.pattern
        if not pattern:
            continue
        matcher = re.compile(pattern) if rule.pattern_type == "regex" else None
        for line_num in body_lines:
            text = lines.get(line_num, "")
            matched = matcher.search(text) if matcher else text.strip() == pattern
            if matched:
                heading_text = matched.group(0) if matcher else pattern
                headings.append((line_num, heading_text, rule.kind or key, "template"))
                break
        else:
            if not rule.optional:
                notes.append(
                    f"Missing required section '{key}' for template {descriptor.id}"
                )

    sections = _finalize_sections(headings, lines, body_lines)

    # add bullet detection per section rules
    for section in sections:
        rule = descriptor.sections.get(section.key) or descriptor.sections.get(
            section.key.lower()
        )
        if rule and rule.split_items:
            section.items = _detect_bullets(lines, section.start_line, section.end_line)
    return sections, notes


# * Detect bullets between start & end lines
def _detect_bullets(lines: Lines, start: int, end: int) -> list[int]:
    bullets: list[int] = []
    for line_num in range(start, end + 1):
        text = lines.get(line_num, "")
        for pattern in BULLET_PATTERNS:
            if pattern.search(text):
                bullets.append(line_num)
                break
    return bullets


# * Generic section detection using LaTeX commands & semantic hints
def _detect_generic_sections(lines: Lines, body_lines: list[int]) -> list[LatexSection]:
    headings: list[tuple[int, str, str, str]] = []
    for line_num in body_lines:
        text = lines.get(line_num, "")
        cmd_match = SECTION_CMD_RE.search(text)
        if cmd_match:
            heading_text = cmd_match.group("title").strip()
            kind = _infer_kind_from_heading(heading_text)
            headings.append((line_num, heading_text, kind, "generic"))
            continue
        for kind, matcher in SEMANTIC_MATCHERS.items():
            if matcher.search(text):
                headings.append((line_num, kind.title(), kind, "semantic"))
                break
    sections = _finalize_sections(headings, lines, body_lines)
    for section in sections:
        section.items = _detect_bullets(lines, section.start_line, section.end_line)
    return sections


# * Analyze LaTeX resume & return structured sections & metadata
def analyze_latex(
    lines: Lines, descriptor: TemplateDescriptor | None = None
) -> LatexAnalysis:
    preamble_lines, body_lines = split_preamble_body(lines)
    notes: list[str] = []

    if descriptor:
        sections, template_notes = _detect_template_sections(
            lines, descriptor, body_lines
        )
        notes.extend(template_notes)
    else:
        sections = []

    if not sections:
        sections = _detect_generic_sections(lines, body_lines)
        if not sections and body_lines:
            # fallback body section
            start_line = body_lines[0]
            end_line = body_lines[-1]
            sections = [
                LatexSection(
                    key="body",
                    heading_text="Body",
                    start_line=start_line,
                    end_line=end_line,
                    confidence=0.4,
                    source="fallback",
                )
            ]

    normalized_order = [s.key.upper() for s in sections]
    return LatexAnalysis(
        sections=sections,
        normalized_order=normalized_order,
        notes=notes,
        descriptor=descriptor,
        preamble_lines=preamble_lines,
        body_lines=body_lines,
    )


# * Build sections JSON payload w/ full keys for readability & compatibility
def sections_to_payload(analysis: LatexAnalysis) -> dict:
    payload_sections: list[dict[str, Any]] = []
    for section in analysis.sections:
        section_entry: dict[str, Any] = {
            "kind": section.key,
            "heading_text": section.heading_text,
            "start_line": section.start_line,
            "end_line": section.end_line,
            "confidence": round(section.confidence, 2),
        }
        if section.items:
            item_label = "ITEM"
            if section.key == "experience":
                item_label = "EXPERIENCE_ITEM"
            elif section.key == "projects":
                item_label = "PROJECT_ITEM"
            elif section.key == "education":
                item_label = "EDUCATION_ITEM"
            section_entry["subsections"] = [
                {"name": item_label, "start_line": ln, "end_line": ln}
                for ln in section.items
            ]
        payload_sections.append(section_entry)

    result: dict[str, Any] = {"sections": payload_sections}
    if analysis.notes:
        result["notes"] = analysis.notes
    if analysis.descriptor:
        meta: dict[str, Any] = {"template_id": analysis.descriptor.id}
        if analysis.descriptor.inline_marker:
            meta["inline_marker"] = analysis.descriptor.inline_marker
        result["meta"] = meta

    return result


# * Extract LaTeX command tokens from text
def _extract_commands(text: str) -> set[str]:
    return set(re.findall(r"\\[A-Za-z]+", text or ""))


# * Determine if line references frozen paths
def _line_hits_frozen_path(text: str, frozen_paths: list[Path]) -> bool:
    stripped = text.strip()
    for frozen in frozen_paths:
        placeholder = frozen.as_posix().removesuffix(".tex")
        if placeholder in stripped:
            return True
    return False


# * Enforce LaTeX-safe editing rules & drop risky ops
def filter_latex_edits(
    edits: dict, resume_lines: Lines, descriptor: TemplateDescriptor | None = None
) -> tuple[dict, list[str]]:
    filtered_ops = []
    notes: list[str] = []
    frozen_patterns = descriptor.frozen.patterns if descriptor else []
    frozen_paths = descriptor.frozen.paths if descriptor else []

    def target_lines(op: dict) -> list[int]:
        if op.get("op") == "replace_line" and "line" in op:
            return [op["line"]]
        if (
            op.get("op") in ("replace_range", "delete_range")
            and "start" in op
            and "end" in op
        ):
            return list(range(op["start"], op["end"] + 1))
        return []

    for op in edits.get("ops", []):
        op_type = op.get("op")
        lines = target_lines(op)
        if op_type == "insert_after":
            anchor = op.get("line")
            if anchor in resume_lines:
                anchor_text = resume_lines[anchor]
                if is_structural_line(anchor_text, frozen_patterns=frozen_patterns):
                    notes.append(f"Skipped insert_after on structural line {anchor}")
                    continue
                if _line_hits_frozen_path(anchor_text, frozen_paths):
                    notes.append(
                        f"Skipped insert_after near frozen include on line {anchor}"
                    )
                    continue
            filtered_ops.append(op)
            continue

        if not lines:
            filtered_ops.append(op)
            continue

        original_commands: set[str] = set()
        risky = False
        for line_num in lines:
            text = resume_lines.get(line_num, "")
            original_commands |= _extract_commands(text)
            if is_structural_line(text, frozen_patterns=frozen_patterns):
                notes.append(f"Skipped {op_type} touching structural line {line_num}")
                risky = True
                break
            if _line_hits_frozen_path(text, frozen_paths):
                notes.append(
                    f"Skipped {op_type} touching frozen path on line {line_num}"
                )
                risky = True
                break
        if risky:
            continue

        if op_type == "delete_range":
            if any(cmd.startswith("\\") for cmd in original_commands):
                notes.append("Dropped delete_range that would remove LaTeX commands")
                continue
            filtered_ops.append(op)
            continue

        replacement_text = op.get("text", "") if isinstance(op, dict) else ""
        new_commands = (
            _extract_commands(replacement_text) if replacement_text else set()
        )

        # ensure bullet commands stick around
        if (
            any(cmd == "\\item" for cmd in original_commands)
            and "\\item" not in new_commands
        ):
            notes.append("Dropped edit removing \\item command")
            continue

        # block edits that erase commands entirely
        retained = all(
            cmd in new_commands or cmd == "\\item" for cmd in original_commands
        )
        if not retained and op_type in ("replace_line", "replace_range"):
            notes.append("Dropped edit removing LaTeX commands")
            continue

        filtered_ops.append(op)

    new_edits = dict(edits)
    new_edits["ops"] = filtered_ops
    return new_edits, notes


# * Validate basic LaTeX syntax (brace balance & document structure)
def validate_basic_latex_syntax(text: str) -> bool:
    # check brace balance
    brace_count = 0
    for char in text:
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count < 0:
                return False
    if brace_count != 0:
        return False

    # check document structure
    has_begin = r"\begin{document}" in text
    has_end = r"\end{document}" in text
    if not (has_begin and has_end):
        return False

    return True


# * Validate LaTeX compilation via subprocess
def validate_latex_compilation(
    content: str, compiler: str = "pdflatex"
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "success": False,
        "compiler_available": True,
        "errors": [],
        "warnings": [],
    }

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = Path(tmpdir) / "test.tex"
            tex_path.write_text(content, encoding="utf-8")

            proc = subprocess.run(
                [compiler, "-interaction=nonstopmode", "-halt-on-error", str(tex_path)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            pdf_path = Path(tmpdir) / "test.pdf"
            if proc.returncode == 0 and pdf_path.exists():
                result["success"] = True
            else:
                result["errors"].append(
                    proc.stderr or proc.stdout or "Compilation failed"
                )

            # extract warnings from stdout
            for line in proc.stdout.split("\n"):
                line_stripped = line.strip()
                if line_stripped and any(
                    w in line for w in ["Warning", "Underfull", "Overfull"]
                ):
                    result["warnings"].append(line_stripped)

    except FileNotFoundError:
        result["compiler_available"] = False
        result["errors"].append(f"LaTeX compiler '{compiler}' not found")
    except subprocess.TimeoutExpired:
        result["errors"].append("LaTeX compilation timed out")

    return result


# * Check availability of LaTeX compilers
def check_latex_availability() -> dict[str, bool]:
    compilers = ["pdflatex", "xelatex", "lualatex"]
    result = {}

    for compiler in compilers:
        try:
            subprocess.run(
                [compiler, "--version"],
                capture_output=True,
                timeout=5,
            )
            result[compiler] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            result[compiler] = False

    return result


# * Validate LaTeX document w/ optional compilation check
def validate_latex_document(
    content: str, check_compilation: bool = True
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "syntax_valid": False,
        "compilation_checked": False,
        "compilation_success": False,
        "errors": [],
        "warnings": [],
    }

    # check syntax first
    if validate_basic_latex_syntax(content):
        result["syntax_valid"] = True
    else:
        result["errors"].append("LaTeX syntax validation failed")
        return result

    # optionally check compilation
    if check_compilation:
        try:
            comp_result = validate_latex_compilation(content)
            result["compilation_checked"] = True
            result["compilation_success"] = comp_result["success"]
            result["errors"].extend(comp_result["errors"])
            result["warnings"].extend(comp_result["warnings"])
        except Exception as e:
            result["errors"].append(f"Compilation validation error: {e}")

    return result


# * Build LaTeX context (descriptor, sections JSON, notes) for LaTeX resume files
def build_latex_context(
    resume_path: Path, lines: Lines, resume_text: str | None = None
) -> tuple[TemplateDescriptor | None, str | None, list[str]]:
    # Build context for LaTeX resume files. Detects template, analyzes sections, & collects notes for LaTeX resume. Tuple of (descriptor, sections_json, notes) for .tex files, or (None, None, []) for non-LaTeX files.
    import json

    descriptor = None
    sections_json = None
    notes: list[str] = []

    if resume_path.suffix.lower() == ".tex":
        # use provided text or read from file
        if resume_text is None:
            resume_text = resume_path.read_text(encoding="utf-8")
        descriptor = detect_template(resume_path, resume_text)
        analysis = analyze_latex(lines, descriptor)
        sections_json = json.dumps(sections_to_payload(analysis), indent=2)
        notes = analysis.notes

    return descriptor, sections_json, notes


__all__ = [
    "TemplateDescriptor",
    "TemplateSectionRule",
    "FrozenRules",
    "LatexSection",
    "LatexAnalysis",
    "load_descriptor",
    "detect_template",
    "analyze_latex",
    "sections_to_payload",
    "filter_latex_edits",
    "validate_basic_latex_syntax",
    "validate_latex_compilation",
    "check_latex_availability",
    "validate_latex_document",
    "build_latex_context",
]
