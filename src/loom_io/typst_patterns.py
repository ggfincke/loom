# src/loom_io/typst_patterns.py
# Typst pattern constants for validation, filtering & document reading

import re
from typing import Tuple

from .shared_patterns import (
    COMMON_SEMANTIC_MATCHERS,
    infer_section_kind as _infer_section_kind,
)

# * Structural prefixes (frozen by default - may start multi-line blocks)
STRUCTURAL_PREFIXES = (
    "#set",
    "#show",
    "#import",
    "#let",
    "#include",
)

# * Section headings: = (level 1), == (level 2), === (level 3), etc.
SECTION_HEADING_RE = re.compile(r"^(=+)\s+(.+)$")

# * Entry function patterns (semantic item boundaries in resume sections)
ENTRY_FUNC_PATTERNS = [
    re.compile(r"#edu\s*\("),
    re.compile(r"#work\s*\("),
    re.compile(r"#project\s*\("),
    re.compile(r"#extracurriculars\s*\("),
    re.compile(r"#entry\s*\("),  # Generic entry function
]

# * Bullet patterns for Typst lists
BULLET_PATTERNS = [
    re.compile(r"^\s*-\s+"),  # Dash lists
    re.compile(r"^\s*\+\s+"),  # Plus lists
    re.compile(r"^\s*\d+\.\s+"),  # Numbered lists
]

# * Comment syntax
COMMENT_LINE_PREFIX = "//"
BLOCK_COMMENT_START = "/*"
BLOCK_COMMENT_END = "*/"

# * Semantic matchers for inferring resume section type from heading text
# Extends common matchers w/ Typst-specific summary pattern
SEMANTIC_MATCHERS = {
    **COMMON_SEMANTIC_MATCHERS,
    "summary": re.compile(r"\bsummary\b|\bobjective\b|\bprofile\b", re.IGNORECASE),
}


# * Check if line starts w/ structural Typst command
def is_structural_prefix(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(STRUCTURAL_PREFIXES)


# * Check if line is a section heading, returns (level, title) or None
def is_section_heading(line: str) -> Tuple[int, str] | None:
    stripped = line.strip()
    match = SECTION_HEADING_RE.match(stripped)
    if match:
        level = len(match.group(1))  # Number of = signs
        title = match.group(2).strip()
        return (level, title)
    return None


# * Check if line starts an entry function (#work, #edu, etc.)
def is_entry_function(line: str) -> bool:
    stripped = line.strip()
    return any(pat.search(stripped) for pat in ENTRY_FUNC_PATTERNS)


# * Check if line is a bullet/list item
def is_bullet_line(line: str) -> bool:
    return any(pat.match(line) for pat in BULLET_PATTERNS)


# * Check if line is a single-line comment
def is_comment_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(COMMENT_LINE_PREFIX)


# * Strip trailing // comment from a line (for delimiter counting)
def strip_trailing_comment(line: str) -> str:
    # Find // that's not inside a string
    in_string = False
    string_char = None
    i = 0
    while i < len(line):
        char = line[i]
        if in_string:
            if char == "\\" and i + 1 < len(line):
                i += 2  # Skip escaped char
                continue
            if char == string_char:
                in_string = False
        else:
            if char == '"':
                in_string = True
                string_char = '"'
            elif i + 1 < len(line) and line[i : i + 2] == "//":
                return line[:i]
        i += 1
    return line


# * Strip string literals from line (for delimiter counting)
def strip_string_literals(line: str) -> str:
    result = []
    in_string = False
    i = 0
    while i < len(line):
        char = line[i]
        if in_string:
            if char == "\\" and i + 1 < len(line):
                i += 2  # Skip escaped char
                continue
            if char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            else:
                result.append(char)
        i += 1
    return "".join(result)


# * Count unbalanced delimiters in a line (after stripping strings/comments)
def count_delimiters(line: str) -> int:
    cleaned = strip_string_literals(strip_trailing_comment(line))
    balance = 0
    balance += cleaned.count("(") - cleaned.count(")")
    balance += cleaned.count("[") - cleaned.count("]")
    balance += cleaned.count("{") - cleaned.count("}")
    return balance


# * Check if line is structural & should not be edited
def is_structural_line(
    text: str,
    frozen_patterns: list[str] | None = None,
    include_comments: bool = False,
) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    # Check structural prefixes
    if stripped.startswith(STRUCTURAL_PREFIXES):
        return True

    # Check frozen patterns from descriptor
    if frozen_patterns and any(pattern in stripped for pattern in frozen_patterns):
        return True

    # Optionally treat comments as structural
    if include_comments and is_comment_line(stripped):
        return True

    return False


# * Check if line contains preservable Typst content
def is_preservable_content(line: str) -> bool:
    if is_structural_line(line, include_comments=True):
        return True
    # Section headings are preservable
    if is_section_heading(line) is not None:
        return True
    return bool(line) and not line.isspace()


# * Check if previous line requires a trailing blank line for readability
def requires_trailing_blank(prev_line: str) -> bool:
    prev_stripped = prev_line.strip()
    # After section headings or closing structural blocks
    if is_section_heading(prev_stripped) is not None:
        return True
    # After lines that close a block (heuristic: ends with ) or ])
    if prev_stripped.endswith(")") or prev_stripped.endswith("]"):
        return True
    return False


# * Infer section type from heading text using semantic matchers
# Typst-specific matcher includes "summary" pattern
_TYPST_EXTRA_MATCHERS = {
    "summary": re.compile(r"\bsummary\b|\bobjective\b|\bprofile\b", re.IGNORECASE),
}


# infer section kind using common + Typst-specific matchers
def infer_section_kind(heading_text: str) -> str | None:
    return _infer_section_kind(heading_text, extra_matchers=_TYPST_EXTRA_MATCHERS)


__all__ = [
    # String constants
    "STRUCTURAL_PREFIXES",
    "COMMENT_LINE_PREFIX",
    "BLOCK_COMMENT_START",
    "BLOCK_COMMENT_END",
    # Regex patterns
    "SECTION_HEADING_RE",
    "ENTRY_FUNC_PATTERNS",
    "BULLET_PATTERNS",
    "SEMANTIC_MATCHERS",
    # Functions
    "is_structural_prefix",
    "is_section_heading",
    "is_entry_function",
    "is_bullet_line",
    "is_comment_line",
    "strip_trailing_comment",
    "strip_string_literals",
    "count_delimiters",
    "is_structural_line",
    "is_preservable_content",
    "requires_trailing_blank",
    "infer_section_kind",
]
