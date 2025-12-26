# src/loom_io/__init__.py
# Package initialization & exports for Loom I/O operations

from .documents import (
    read_docx,
    read_resume,
    read_latex,
    write_docx,
    write_text_lines,
    read_text,
    read_docx_with_formatting,
    apply_edits_to_docx,
)
from .generics import (
    write_json_safe,
    read_json_safe,
    ensure_parent,
    exit_with_error,
    number_lines,
)
from .types import Lines
from .latex_handler import (
    detect_template,
    analyze_latex,
    sections_to_payload,
    filter_latex_edits,
    TemplateDescriptor,
    load_descriptor,
)

__all__ = [
    "read_docx",
    "read_resume",
    "read_latex",
    "write_docx",
    "write_text_lines",
    "read_text",
    "read_docx_with_formatting",
    "apply_edits_to_docx",
    "write_json_safe",
    "read_json_safe",
    "ensure_parent",
    "exit_with_error",
    "number_lines",
    "Lines",
    "detect_template",
    "analyze_latex",
    "sections_to_payload",
    "filter_latex_edits",
    "TemplateDescriptor",
    "load_descriptor",
]
