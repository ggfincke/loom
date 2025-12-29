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
    get_handler,
    clear_handler_cache,
)
from .generics import (
    write_json_safe,
    read_json_safe,
    ensure_parent,
    exit_with_error,
)

# Shared template & pattern utilities
from .template_io import (
    TEMPLATE_FILENAME,
    TemplateDescriptor,
    TemplateSectionRule,
    FrozenRules,
    find_template_descriptor_path,
    load_descriptor,
)
from .shared_patterns import (
    COMMON_SEMANTIC_MATCHERS,
    infer_section_kind,
)
from .types import (
    DocumentSection,
    DocumentAnalysis,
)

# Base handler class
from .base_handler import BaseDocumentHandler

# Handler classes (OO API)
from .latex_handler import LatexHandler
from .typst_handler import TypstHandler

# Typst frozen range utilities (useful externally)
from .typst_handler import (
    find_frozen_ranges,
    is_in_frozen_range,
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
    # Handler registry (primary API)
    "get_handler",
    "clear_handler_cache",
    # Generics
    "write_json_safe",
    "read_json_safe",
    "ensure_parent",
    "exit_with_error",
    # Shared template utilities
    "TEMPLATE_FILENAME",
    "TemplateDescriptor",
    "TemplateSectionRule",
    "FrozenRules",
    "find_template_descriptor_path",
    "load_descriptor",
    # Shared pattern utilities
    "COMMON_SEMANTIC_MATCHERS",
    "infer_section_kind",
    # Unified types
    "DocumentSection",
    "DocumentAnalysis",
    # Handler classes (OO API)
    "BaseDocumentHandler",
    "LatexHandler",
    "TypstHandler",
    # Typst frozen range utilities
    "find_frozen_ranges",
    "is_in_frozen_range",
    # Bulk I/O
    "discover_jobs",
    "deduplicate_job_specs",
    "create_bulk_output_layout",
    "write_run_metadata",
    "write_job_artifacts",
    "write_matrix_files",
]
