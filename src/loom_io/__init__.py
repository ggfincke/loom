# src/loom_io/__init__.py
# Package initialization and exports for Loom I/O operations

# i/o utils for Loom
from .documents import (
    read_docx, 
    write_docx, 
    number_lines, 
    read_text,
    read_docx_with_formatting,
    apply_edits_to_docx
)
from .generics import write_json_safe, read_json_safe, ensure_parent, exit_with_error
from .types import Lines

__all__ = [
    "read_docx",
    "write_docx", 
    "number_lines",
    "read_text",
    "read_docx_with_formatting",
    "apply_edits_to_docx",
    "write_json_safe",
    "read_json_safe", 
    "ensure_parent",
    "exit_with_error",
    "Lines",
]