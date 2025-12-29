# src/core/edit_helpers.py
# Shared edit helper functions for pipeline & validation modules
# Consolidates duplicated functions to provide single source of truth

from typing import Optional, List

from .types import Lines


# =============================================================================
# Line existence validation
# =============================================================================


# * Check if a specific line exists in the lines dictionary
def check_line_exists(line: int, lines: Lines) -> bool:
    return line in lines


# * Check if all lines in a range exist; returns (exists, first_missing_line)
def check_range_exists(
    start: int, end: int, lines: Lines
) -> tuple[bool, Optional[int]]:
    for line in range(start, end + 1):
        if line not in lines:
            return False, line
    return True, None


# =============================================================================
# Text line counting
# =============================================================================


# * Count lines in text string; optionally counts empty string as 1 line
def count_text_lines(text: str, allow_empty: bool = False) -> int:
    if not text:
        return 1 if allow_empty else 0
    return len(text.split("\n"))


# =============================================================================
# Operation helpers
# =============================================================================


# * Get operation line number (for sorting); prefers 'line' field over 'start'
def get_operation_line(op: dict) -> int:
    if "line" in op:
        return op["line"]
    elif "start" in op:
        return op["start"]
    else:
        return 0


# * Collect lines to move after a position; returns list sorted descending
def collect_lines_to_move(lines: Lines, after_line: int) -> list[tuple[int, str]]:
    return sorted(
        [(k, v) for k, v in lines.items() if k > after_line],
        key=lambda t: t[0],
        reverse=True,
    )


# * Shift lines by delta; modifies lines dict in place
def shift_lines(
    lines: Lines,
    lines_to_move: list[tuple[int, str]],
    delta: int,
) -> None:
    # delete original positions
    for k, v in lines_to_move:
        del lines[k]

    # reinsert at shifted positions
    for k, v in lines_to_move:
        lines[k + delta] = v
