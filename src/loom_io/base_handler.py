# src/loom_io/base_handler.py
# Abstract base class for document format handlers

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Pattern, Tuple

from .types import DocumentSection, DocumentAnalysis
from .template_io import (
    TemplateDescriptor,
    FrozenRules,
    find_template_descriptor_path,
    load_descriptor,
    detect_inline_marker,
)
from ..core.types import Lines


# * Abstract base handler for document formats (LaTeX, Typst, etc.)
# Provides shared logic for template detection, section analysis, edit filtering & validation
# Subclasses implement format-specific patterns & parsing
class BaseDocumentHandler(ABC):

    # === Class Attributes (subclass must set) ===
    format_type: str  # "latex" | "typst"

    # === Abstract Properties ===

    # regex pattern for inline template markers in this format (must have named group 'id')
    @property
    @abstractmethod
    def inline_marker_pattern(self) -> Pattern[str]: ...

    # max lines to search for inline marker (None = entire file)
    @property
    @abstractmethod
    def inline_marker_max_lines(self) -> int | None: ...

    # section type matchers for this format (maps kind to regex patterns for heading text)
    @property
    @abstractmethod
    def semantic_matchers(self) -> dict[str, Pattern[str]]: ...

    # === Shared Template Detection ===

    # detect inline template marker in document content
    def detect_inline_marker(self, content: str) -> str | None:
        return detect_inline_marker(
            content,
            self.inline_marker_pattern,
            max_lines=self.inline_marker_max_lines,
        )

    # detect template from file path & content (priority: descriptor file > inline marker > None)
    def detect_template(
        self, resume_path: Path, content: str
    ) -> TemplateDescriptor | None:
        inline_marker = self.detect_inline_marker(content)
        descriptor_path = find_template_descriptor_path(resume_path)

        if descriptor_path:
            return load_descriptor(descriptor_path, inline_marker)

        if inline_marker:
            return self._create_inline_only_descriptor(inline_marker)

        return None

    # create minimal descriptor from inline marker only
    def _create_inline_only_descriptor(self, marker: str) -> TemplateDescriptor:
        return TemplateDescriptor(
            id=marker,
            type="resume",
            name=None,
            version=None,
            sections={},
            frozen=FrozenRules(),
            custom={},
            inline_marker=marker,
            inline_only=True,
        )

    # === Abstract Analysis Methods ===

    # analyze document & extract sections (returns DocumentAnalysis w/ sections, notes & metadata)
    @abstractmethod
    def analyze(
        self, lines: Lines, descriptor: TemplateDescriptor | None = None
    ) -> DocumentAnalysis: ...

    # check if line is structural & should not be edited (setup, imports, function defs, etc.)
    @abstractmethod
    def is_structural_line(
        self, line: str, frozen_patterns: list[str] | None = None
    ) -> bool: ...

    # === Shared Payload Generation ===

    # * Convert analysis to JSON-serializable payload for AI (normalized format across all handlers)
    def sections_to_payload(self, analysis: DocumentAnalysis) -> dict[str, Any]:
        return {
            "sections": [
                {
                    "kind": s.kind or s.key,
                    "key": s.key,
                    "heading_text": s.heading_text,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "confidence": round(s.confidence, 2) if s.confidence else None,
                    "items": s.items if s.items else [],
                }
                for s in analysis.sections
            ],
            "section_order": analysis.normalized_order,
            "notes": analysis.notes,
            "template_id": analysis.descriptor.id if analysis.descriptor else None,
        }

    # === Edit Filtering ===

    # * Filter edits to protect structural content (returns filtered_edits & notes)
    def filter_edits(
        self,
        edits: dict,
        lines: Lines,
        descriptor: TemplateDescriptor | None = None,
        **kwargs,
    ) -> Tuple[dict, list[str]]:
        notes: list[str] = []
        filtered_ops: list[dict] = []
        frozen_patterns = descriptor.frozen.patterns if descriptor else []

        for op in edits.get("ops", []):
            op_type = op.get("op") or op.get("operation", "")
            line_num = op.get("line") or op.get("line_number")
            start_line = op.get("start") or op.get("start_line")
            end_line = op.get("end") or op.get("end_line")

            # Determine affected lines
            affected_lines: list[int] = []
            if line_num is not None:
                affected_lines = [line_num]
            elif start_line is not None and end_line is not None:
                affected_lines = list(range(start_line, end_line + 1))

            if not affected_lines:
                # No specific line target - pass through
                filtered_ops.append(op)
                continue

            # Check each affected line
            skip = False
            for ln in affected_lines:
                line_text = lines.get(ln, "")

                # Check frozen patterns from descriptor
                if self._is_frozen_by_descriptor(line_text, descriptor):
                    notes.append(f"Skipped {op_type} on frozen line {ln}")
                    skip = True
                    break

                # Check structural lines
                if self.is_structural_line(line_text, frozen_patterns):
                    notes.append(f"Skipped {op_type} on structural line {ln}")
                    skip = True
                    break

                # Format-specific additional checks
                if not self._check_frozen_ranges(ln, kwargs):
                    notes.append(f"Skipped {op_type} on frozen range line {ln}")
                    skip = True
                    break

            if skip:
                continue

            # Format-specific edit validation
            if not self._validate_edit(op, lines, affected_lines, notes):
                continue

            filtered_ops.append(op)

        return {
            "version": edits.get("version", 1),
            "meta": edits.get("meta", {}),
            "ops": filtered_ops,
        }, notes

    # check if line is frozen by descriptor patterns
    def _is_frozen_by_descriptor(
        self, line_text: str, descriptor: TemplateDescriptor | None
    ) -> bool:
        if not descriptor:
            return False
        for pattern in descriptor.frozen.patterns:
            if pattern in line_text:
                return True
        return False

    # check if line is in a frozen range (returns True if OK to edit, False if frozen)
    def _check_frozen_ranges(self, line_num: int, kwargs: dict) -> bool:
        return True  # base: no frozen ranges

    # format-specific edit validation (returns True to keep edit, False to drop)
    @abstractmethod
    def _validate_edit(
        self, op: dict, lines: Lines, affected_lines: list[int], notes: list[str]
    ) -> bool: ...

    # === Validation ===

    # validate basic syntax (balanced delimiters, etc.)
    @abstractmethod
    def validate_syntax(self, content: str) -> bool: ...

    # attempt compilation & return result dict w/ 'success', 'errors', 'warnings'
    @abstractmethod
    def validate_compilation(self, content: str) -> dict[str, Any]: ...

    # check if compilation tool(s) are available (returns dict mapping tool name to bool)
    @abstractmethod
    def check_tool_availability(self) -> dict[str, bool]: ...

    # * Full document validation (syntax + optional compilation)
    def validate_document(
        self, content: str, check_compilation: bool = True
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "syntax_valid": False,
            "compilation_checked": False,
            "compilation_success": None,
            "errors": [],
            "warnings": [],
        }

        if not self.validate_syntax(content):
            result["errors"].append(
                f"Basic {self.format_type} syntax validation failed"
            )
            return result

        result["syntax_valid"] = True

        if check_compilation:
            try:
                comp_result = self.validate_compilation(content)
                result["compilation_checked"] = True
                result["compilation_success"] = comp_result.get("success", False)
                result["errors"].extend(comp_result.get("errors", []))
                result["warnings"].extend(comp_result.get("warnings", []))
            except Exception as e:
                result["errors"].append(f"Compilation validation error: {e}")

        return result

    # === Context Building ===

    # * Build context for AI processing (combines template detection & analysis)
    def build_context(
        self, resume_path: Path, lines: Lines, text: str
    ) -> Tuple[TemplateDescriptor | None, DocumentAnalysis]:
        descriptor = self.detect_template(resume_path, text)
        analysis = self.analyze(lines, descriptor)
        return descriptor, analysis


__all__ = [
    "BaseDocumentHandler",
]
