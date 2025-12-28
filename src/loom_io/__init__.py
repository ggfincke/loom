# src/loom_io/__init__.py
# Package initialization & exports for Loom I/O operations

from .documents import (
    read_docx,
    read_resume,
    read_latex,
    read_typst,
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
)
from .latex_handler import (
    detect_template,
    analyze_latex,
    sections_to_payload,
    filter_latex_edits,
    TemplateDescriptor,
    load_descriptor,
    build_latex_context,
)
from .typst_handler import (
    build_typst_context,
    analyze_typst,
    sections_to_payload as typst_sections_to_payload,
    filter_typst_edits,
    TypstSection,
    TypstAnalysis,
)
from .bulk_io import (
    discover_jobs,
    deduplicate_job_specs,
    create_bulk_output_layout,
    write_run_metadata,
    write_job_artifacts,
    write_matrix_files,
)

__all__ = [
    # Document I/O
    "read_docx",
    "read_resume",
    "read_latex",
    "read_typst",
    "write_docx",
    "write_text_lines",
    "read_text",
    "read_docx_with_formatting",
    "apply_edits_to_docx",
    # Generics
    "write_json_safe",
    "read_json_safe",
    "ensure_parent",
    "exit_with_error",
    # LaTeX
    "detect_template",
    "analyze_latex",
    "sections_to_payload",
    "filter_latex_edits",
    "TemplateDescriptor",
    "load_descriptor",
    "build_latex_context",
    # Typst
    "build_typst_context",
    "analyze_typst",
    "typst_sections_to_payload",
    "filter_typst_edits",
    "TypstSection",
    "TypstAnalysis",
    # Bulk I/O
    "discover_jobs",
    "deduplicate_job_specs",
    "create_bulk_output_layout",
    "write_run_metadata",
    "write_job_artifacts",
    "write_matrix_files",
]
