# src/loom_io/latex_patterns.py
# Shared LaTeX pattern constants for validation, filtering & document reading

# * Structural commands that define document architecture
STRUCTURAL_PREFIXES = (
    "\\documentclass",    # Document type declaration
    "\\usepackage",       # Package imports
    "\\newcommand",       # Custom command definitions
    "\\renewcommand",     # Command redefinitions
    "\\begin{",           # Environment starts
    "\\end{",             # Environment ends
    "\\input{",           # File includes
    "\\include{",         # File includes (LaTeX-specific)
)

# * Section-level structural commands
SECTION_PREFIXES = (
    "\\section",
    "\\subsection",
    "\\subsubsection",
)

# * Item/bullet commands
ITEM_COMMANDS = (
    "\\item",
)

# * Document structure markers for validation
DOCUMENT_MARKERS = {
    "documentclass": "\\documentclass",
    "begin_document": "\\begin{document}",
    "end_document": "\\end{document}",
}

# * Special line prefixes (comments, etc.)
SPECIAL_PREFIXES = (
    "%",  # LaTeX comments
)


# * Check if line starts w/ structural LaTeX command
def is_structural_prefix(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(STRUCTURAL_PREFIXES)


# * Check if line starts w/ section-level command
def is_section_command(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(SECTION_PREFIXES)


# * Check if text contains required LaTeX document structure
def has_required_document_structure(text: str) -> tuple[bool, bool, bool]:
    return (
        DOCUMENT_MARKERS["documentclass"] in text,
        DOCUMENT_MARKERS["begin_document"] in text,
        DOCUMENT_MARKERS["end_document"] in text,
    )
