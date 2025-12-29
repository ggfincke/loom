# src/loom_io/types.py
# Shared type definitions for document handlers

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

# Re-export template types for convenience
from .template_io import (
    TemplateDescriptor,
    TemplateSectionRule,
    FrozenRules,
)

# Re-export Lines for backward compatibility (canonical location: core.types)
from ..core.types import Lines


# unified section representation for all document formats (LaTeX, Typst, etc.)
@dataclass
class DocumentSection:
    key: str
    heading_text: str
    start_line: int
    end_line: int
    confidence: float
    items: list[int] = field(default_factory=list)
    source: str = "generic"  # "generic" | "template"
    kind: str | None = None  # semantic kind (experience, education, etc.)


# unified analysis result for all document formats w/ format-specific metadata
@dataclass
class DocumentAnalysis:
    sections: list[DocumentSection]
    normalized_order: list[str]
    notes: list[str]
    descriptor: TemplateDescriptor | None
    format_type: str  # "latex" | "typst"
    # Format-specific metadata (optional based on format_type)
    frozen_ranges: list[Tuple[int, int]] | None = None  # Typst
    preamble_lines: list[int] | None = None  # LaTeX
    header_lines: list[int] | None = None  # Typst (structural lines at start)
    body_lines: list[int] | None = None  # LaTeX


__all__ = [
    # Template types (re-exported from template_io)
    "TemplateDescriptor",
    "TemplateSectionRule",
    "FrozenRules",
    # Document types
    "DocumentSection",
    "DocumentAnalysis",
    # Backward compatibility (canonical location: core.types)
    "Lines",
]
