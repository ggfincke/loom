# src/loom_io/latex_patterns.py
# LaTeX pattern constants for validation, filtering & document reading

import re

from .shared_patterns import COMMON_SEMANTIC_MATCHERS

# * Structural commands that define document architecture
STRUCTURAL_PREFIXES = (
    "\\documentclass",  # Document type declaration
    "\\usepackage",  # Package imports
    "\\newcommand",  # Custom command definitions
    "\\renewcommand",  # Command redefinitions
    "\\begin{",  # Environment starts
    "\\end{",  # Environment ends
    "\\input{",  # File includes
    "\\include{",  # File includes (LaTeX-specific)
)

# * Section-level structural commands
SECTION_PREFIXES = (
    "\\section",
    "\\subsection",
    "\\subsubsection",
)

# * Item/bullet commands
ITEM_COMMANDS = ("\\item",)

# * Document structure markers for validation
DOCUMENT_MARKERS = {
    "documentclass": "\\documentclass",
    "begin_document": "\\begin{document}",
    "end_document": "\\end{document}",
}

# * Special line prefixes (comments, etc.)
SPECIAL_PREFIXES = ("%",)  # LaTeX comments

# * Compiled regex for section command detection (section, subsection, etc.)
SECTION_CMD_RE = re.compile(
    r"\\(?P<cmd>section\*?|subsection\*?|subsubsection\*?|cvsection|sectionhead)"
    r"\s*{\s*(?P<title>[^}]*)\s*}"
)

# * Semantic matchers for inferring resume section type from heading text
# Extends common matchers w/ LaTeX-specific heading pattern
SEMANTIC_MATCHERS = {
    **COMMON_SEMANTIC_MATCHERS,
    "heading": re.compile(r"\\name{|\\contact", re.IGNORECASE),
}

# * Bullet/item patterns for detecting list entries in LaTeX documents
BULLET_PATTERNS = [
    re.compile(r"\\item\b"),
    re.compile(r"\\entry\b"),
    re.compile(r"\\cventry\b"),
    re.compile(r"\\cvitem\b"),
]


# * Check if line starts w/ structural LaTeX command
def is_structural_prefix(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(STRUCTURAL_PREFIXES)


# * Check if line starts w/ section-level command
def is_section_command(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(SECTION_PREFIXES)


# * Check if line starts w/ any protected LaTeX prefix (structural, section, item, or special)
def is_protected_prefix(line: str) -> bool:
    stripped = line.strip()
    all_prefixes = (
        STRUCTURAL_PREFIXES + SECTION_PREFIXES + ITEM_COMMANDS + SPECIAL_PREFIXES
    )
    return stripped.startswith(all_prefixes)


# * Check if text contains required LaTeX document structure
def has_required_document_structure(text: str) -> tuple[bool, bool, bool]:
    return (
        DOCUMENT_MARKERS["documentclass"] in text,
        DOCUMENT_MARKERS["begin_document"] in text,
        DOCUMENT_MARKERS["end_document"] in text,
    )


# * Check if line is structural & should not be edited (unified function)
def is_structural_line(
    text: str,
    frozen_patterns: list[str] | None = None,
    include_all_protected: bool = False,
) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    if include_all_protected:
        if is_protected_prefix(stripped):
            return True
    else:
        if stripped.startswith(STRUCTURAL_PREFIXES):
            return True

    if frozen_patterns and any(pattern in stripped for pattern in frozen_patterns):
        return True

    return False


# * Check if line contains preservable LaTeX content (structural or non-empty)
def is_preservable_content(line: str) -> bool:
    if is_structural_line(line, include_all_protected=True):
        return True
    return bool(line) and not line.isspace()


# * Check if previous line requires a trailing blank line for readability
def requires_trailing_blank(prev_line: str) -> bool:
    prev_stripped = prev_line.strip()
    return prev_stripped.startswith("\\end{") or is_section_command(prev_line)


__all__ = [
    # String constants
    "STRUCTURAL_PREFIXES",
    "SECTION_PREFIXES",
    "ITEM_COMMANDS",
    "DOCUMENT_MARKERS",
    "SPECIAL_PREFIXES",
    # Regex patterns
    "SECTION_CMD_RE",
    "SEMANTIC_MATCHERS",
    "BULLET_PATTERNS",
    # Functions
    "is_structural_prefix",
    "is_section_command",
    "is_protected_prefix",
    "has_required_document_structure",
    "is_structural_line",
    "is_preservable_content",
    "requires_trailing_blank",
]
