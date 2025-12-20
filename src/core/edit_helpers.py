# src/core/edit_helpers.py
# Shared validation & utility functions for edit operations (validate_edits & apply_edits)

from typing import List, Optional, Tuple

from ..loom_io.types import Lines


# * Operation type constants
OP_REPLACE_LINE = "replace_line"
OP_REPLACE_RANGE = "replace_range"
OP_INSERT_AFTER = "insert_after"
OP_DELETE_RANGE = "delete_range"


# * Line existence validation
def check_line_exists(line: int, lines: Lines) -> bool:
    return line in lines


# * Range existence validation
def check_range_exists(start: int, end: int, lines: Lines) -> Tuple[bool, Optional[int]]:
    for line in range(start, end + 1):
        if line not in lines:
            return False, line
    return True, None


# * Line count calculation from text
def count_text_lines(text: str, allow_empty: bool = False) -> int:
    if not text:
        return 1 if allow_empty else 0
    return len(text.split("\n"))


# * Integer type & bounds validation
def validate_line_number(line: any, op_index: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    if not isinstance(line, int):
        prefix = f"Op {op_index}: " if op_index is not None else ""
        return False, f"{prefix}'line' must be integer >= 1"

    if line < 1:
        prefix = f"Op {op_index}: " if op_index is not None else ""
        return False, f"{prefix}'line' must be integer >= 1"

    return True, None


# * Range bounds validation
def validate_range_bounds(
    start: any, end: any, op_index: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    prefix = f"Op {op_index}: " if op_index is not None else ""

    if not isinstance(start, int) or not isinstance(end, int):
        return False, f"{prefix}start and end must be integers"

    if start < 1 or end < 1 or start > end:
        return False, f"{prefix}invalid range {start}-{end}"

    return True, None


# * Required field validation
def validate_required_fields(
    op: dict, required_fields: List[str], op_type: str, op_index: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    prefix = f"Op {op_index}: " if op_index is not None else ""
    missing = [f for f in required_fields if f not in op]

    if missing:
        fields_str = ", ".join(missing)
        return False, f"{prefix}{op_type} missing required fields ({fields_str})"

    return True, None


# * Text type validation
def validate_text_field(
    text: any, allow_newlines: bool = True, op_index: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    prefix = f"Op {op_index}: " if op_index is not None else ""

    if not isinstance(text, str):
        return False, f"{prefix}'text' must be string"

    if not allow_newlines and "\n" in text:
        return False, f"{prefix}replace_line text contains newline; use replace_range"

    return True, None


# * Get operation line number (for sorting)
def get_operation_line(op: dict) -> int:
    if "line" in op:
        return op["line"]
    elif "start" in op:
        return op["start"]
    else:
        return 0


# =============================================================================
# Shared helpers for validation & apply (consolidated from validation.py & pipeline.py)
# =============================================================================


# * Check range for duplicate line usage (used by validate_edits)
def check_range_usage(
    start: int,
    end: int,
    line_usage: dict[int, str],
    op_type: str,
    op_index: int,
) -> List[str]:
    warnings: List[str] = []

    # check for duplicates first
    for line in range(start, end + 1):
        if line in line_usage:
            warnings.append(f"Op {op_index}: duplicate operation on line {line}")
            break  # only report first duplicate

    # mark all lines as used regardless
    for line in range(start, end + 1):
        line_usage[line] = op_type

    return warnings


# * Validate cross-operation interactions (used by validate_edits)
def validate_operation_interactions(ops: List[dict]) -> List[str]:
    warnings: List[str] = []

    # 1. Check for insert_after on lines being deleted
    delete_ranges = [
        (op["start"], op["end"])
        for op in ops
        if op.get("op") == OP_DELETE_RANGE and "start" in op and "end" in op
    ]
    for i, op in enumerate(ops):
        if op.get("op") == OP_INSERT_AFTER and "line" in op:
            ln = op["line"]
            if any(s <= ln <= e for s, e in delete_ranges):
                warnings.append(
                    f"Op {i}: insert_after on line {ln} that is deleted by a delete_range"
                )

    # 2. Check for delete_range overlapping replace_range
    replace_ranges = [
        (op["start"], op["end"])
        for op in ops
        if op.get("op") == OP_REPLACE_RANGE and "start" in op and "end" in op
    ]
    for i, op in enumerate(ops):
        if op.get("op") == OP_DELETE_RANGE and "start" in op and "end" in op:
            s, e = op["start"], op["end"]
            if any(not (e2 < s or s2 > e) for (s2, e2) in replace_ranges):
                warnings.append(
                    f"Op {i}: delete_range overlaps a replace_range; split or reorder ops"
                )

    # 3. Check for multiple insert_after on same line
    seen_inserts: set[int] = set()
    for i, op in enumerate(ops):
        if op.get("op") == OP_INSERT_AFTER and "line" in op:
            ln = op["line"]
            if ln in seen_inserts:
                warnings.append(f"Op {i}: multiple insert_after on line {ln}")
            seen_inserts.add(ln)

    return warnings


# * Collect lines to move after a position (used by apply_edits)
def collect_lines_to_move(lines: Lines, after_line: int) -> List[Tuple[int, str]]:
    return sorted(
        [(k, v) for k, v in lines.items() if k > after_line],
        key=lambda t: t[0],
        reverse=True,
    )


# * Shift lines by delta (used by apply_edits)
def shift_lines(
    lines: Lines,
    lines_to_move: List[Tuple[int, str]],
    delta: int,
) -> None:
    # delete original positions
    for k, v in lines_to_move:
        del lines[k]

    # reinsert at shifted positions
    for k, v in lines_to_move:
        lines[k + delta] = v
