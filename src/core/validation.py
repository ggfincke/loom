# src/core/validation.py
# Pure validation logic for edit operations (no I/O)

from dataclasses import dataclass, field
from typing import List, Any, Optional
from .constants import (
    RiskLevel,
    OP_REPLACE_LINE,
    OP_REPLACE_RANGE,
    OP_INSERT_AFTER,
    OP_DELETE_RANGE,
)

from .types import Lines
from .edit_helpers import check_line_exists, check_range_exists, count_text_lines


# * Standard result type for validation operations (pure data, no I/O)
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# * Integer type & bounds validation
def validate_line_number(
    line: any, op_index: Optional[int] = None
) -> tuple[bool, Optional[str]]:
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
) -> tuple[bool, Optional[str]]:
    prefix = f"Op {op_index}: " if op_index is not None else ""

    if not isinstance(start, int) or not isinstance(end, int):
        return False, f"{prefix}start and end must be integers"

    if start < 1 or end < 1 or start > end:
        return False, f"{prefix}invalid range {start}-{end}"

    return True, None


# * Required field validation
def validate_required_fields(
    op: dict, required_fields: List[str], op_type: str, op_index: Optional[int] = None
) -> tuple[bool, Optional[str]]:
    prefix = f"Op {op_index}: " if op_index is not None else ""
    missing = [f for f in required_fields if f not in op]

    if missing:
        fields_str = ", ".join(missing)
        return False, f"{prefix}{op_type} missing required fields ({fields_str})"

    return True, None


# * Text type validation
def validate_text_field(
    text: any, allow_newlines: bool = True, op_index: Optional[int] = None
) -> tuple[bool, Optional[str]]:
    prefix = f"Op {op_index}: " if op_index is not None else ""

    if not isinstance(text, str):
        return False, f"{prefix}'text' must be string"

    if not allow_newlines and "\n" in text:
        return False, f"{prefix}replace_line text contains newline; use replace_range"

    return True, None


# * Check range for duplicate line usage
def check_range_usage(
    start: int,
    end: int,
    line_usage: dict[int, str],
    op_type: str,
    op_index: int,
) -> List[str]:
    warnings: List[str] = []

    for line in range(start, end + 1):
        if line in line_usage:
            warnings.append(f"Op {op_index}: duplicate operation on line {line}")
            break

    for line in range(start, end + 1):
        line_usage[line] = op_type

    return warnings


# * Validate cross-operation interactions
def validate_operation_interactions(ops: List[dict]) -> List[str]:
    warnings: List[str] = []

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

    seen_inserts: set[int] = set()
    for i, op in enumerate(ops):
        if op.get("op") == OP_INSERT_AFTER and "line" in op:
            ln = op["line"]
            if ln in seen_inserts:
                warnings.append(f"Op {i}: multiple insert_after on line {ln}")
            seen_inserts.add(ln)

    return warnings


# * Validation outcome for strategy results
@dataclass
class ValidationOutcome:
    success: bool
    value: Any = None
    should_continue: bool = False


# * Edit JSON validation logic (moved from pipeline.py)
def validate_edits(
    edits: dict, resume_lines: dict[int, str], risk: RiskLevel
) -> List[str]:
    warnings: List[str] = []

    if "ops" not in edits:
        warnings.append("Missing 'ops' field in edits")
        return warnings

    ops = edits["ops"]
    if not isinstance(ops, list):
        warnings.append("'ops' field must be a list")
        return warnings

    if len(ops) == 0:
        warnings.append("'ops' list is empty")
        return warnings

    line_usage: dict[int, str] = {}

    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            warnings.append(f"Op {i}: must be an object")
            continue

        op_type = op.get("op")
        if not op_type:
            warnings.append(f"Op {i}: missing 'op' field")
            continue

        if op_type == OP_REPLACE_LINE:
            is_valid, error = validate_required_fields(
                op, ["line", "text"], "replace_line", i
            )
            if not is_valid:
                warnings.append(error)
                continue

            line = op["line"]
            is_valid, error = validate_line_number(line, i)
            if not is_valid:
                warnings.append(error)
                continue

            is_valid, error = validate_text_field(
                op["text"], allow_newlines=False, op_index=i
            )
            if not is_valid:
                warnings.append(error)
                continue

            if not check_line_exists(line, resume_lines):
                warnings.append(f"Op {i}: line {line} not in resume bounds")
                continue

            if line in line_usage:
                warnings.append(f"Op {i}: duplicate operation on line {line}")
            line_usage[line] = op_type

        elif op_type == OP_REPLACE_RANGE:
            is_valid, error = validate_required_fields(
                op, ["start", "end", "text"], "replace_range", i
            )
            if not is_valid:
                warnings.append(error)
                continue

            start, end = op["start"], op["end"]
            is_valid, error = validate_range_bounds(start, end, i)
            if not is_valid:
                warnings.append(error)
                continue

            is_valid, error = validate_text_field(
                op["text"], allow_newlines=True, op_index=i
            )
            if not is_valid:
                warnings.append(error)
                continue

            exists, missing_line = check_range_exists(start, end, resume_lines)
            if not exists:
                warnings.append(f"Op {i}: line {missing_line} not in resume bounds")
                continue

            text_line_count = count_text_lines(op["text"])
            range_line_count = end - start + 1
            if text_line_count != range_line_count:
                msg = f"Op {i}: replace_range line count mismatch ({range_line_count} -> {text_line_count})"
                if risk in [RiskLevel.MED, RiskLevel.HIGH, RiskLevel.STRICT]:
                    warnings.append(msg + " (will cause line collisions)")
                else:
                    warnings.append(msg)

            dup_warnings = check_range_usage(start, end, line_usage, op_type, i)
            warnings.extend(dup_warnings)

        elif op_type == OP_INSERT_AFTER:
            is_valid, error = validate_required_fields(
                op, ["line", "text"], "insert_after", i
            )
            if not is_valid:
                warnings.append(error)
                continue

            line = op["line"]
            is_valid, error = validate_line_number(line, i)
            if not is_valid:
                warnings.append(error)
                continue

            is_valid, error = validate_text_field(
                op["text"], allow_newlines=True, op_index=i
            )
            if not is_valid:
                warnings.append(error)
                continue

            if not check_line_exists(line, resume_lines):
                warnings.append(f"Op {i}: line {line} not in resume bounds")
                continue

        elif op_type == OP_DELETE_RANGE:
            is_valid, error = validate_required_fields(
                op, ["start", "end"], "delete_range", i
            )
            if not is_valid:
                warnings.append(error)
                continue

            start, end = op["start"], op["end"]
            is_valid, error = validate_range_bounds(start, end, i)
            if not is_valid:
                warnings.append(error)
                continue

            exists, missing_line = check_range_exists(start, end, resume_lines)
            if not exists:
                warnings.append(f"Op {i}: line {missing_line} not in resume bounds")
                continue

            dup_warnings = check_range_usage(start, end, line_usage, op_type, i)
            warnings.extend(dup_warnings)

        else:
            warnings.append(f"Op {i}: unknown operation type '{op_type}'")

    warnings.extend(validate_operation_interactions(ops))

    return warnings
