# src/core/types.py
# Core type definitions used throughout Loom

# Line number to text content mapping (1-indexed)
Lines = dict[int, str]


# * Format resume lines w/ right-aligned 4-char line numbers
def number_lines(lines: Lines) -> str:
    return "\n".join(f"{i:>4} {text}" for i, text in sorted(lines.items()))
