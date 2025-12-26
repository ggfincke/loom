# src/core/pipeline.py
# Core processing pipeline for edit generation, validation, & application

from typing import List
import difflib
from datetime import datetime, timezone
from .exceptions import EditError
from ..ai.prompts import (
    build_generate_prompt,
    build_edit_prompt,
    build_prompt_operation_prompt,
)
from ..ai.clients import run_generate
from ..ai.utils import process_ai_response

from ..loom_io.types import Lines
from ..loom_io import number_lines
from .constants import (
    EditOperation,
    OP_REPLACE_LINE,
    OP_REPLACE_RANGE,
    OP_INSERT_AFTER,
    OP_DELETE_RANGE,
)
from .debug import debug_ai


# =============================================================================
# Edit application helpers (inlined from edit_helpers.py)
# =============================================================================


# * Line existence validation
def check_line_exists(line: int, lines: Lines) -> bool:
    return line in lines


# * Range existence validation
def check_range_exists(
    start: int, end: int, lines: Lines
) -> tuple[bool, int | None]:
    for line in range(start, end + 1):
        if line not in lines:
            return False, line
    return True, None


# * Line count calculation from text
def count_text_lines(text: str, allow_empty: bool = False) -> int:
    if not text:
        return 1 if allow_empty else 0
    return len(text.split("\n"))


# * Get operation line number (for sorting)
def get_operation_line(op: dict) -> int:
    if "line" in op:
        return op["line"]
    elif "start" in op:
        return op["start"]
    else:
        return 0


# * Collect lines to move after a position
def collect_lines_to_move(lines: Lines, after_line: int) -> list[tuple[int, str]]:
    return sorted(
        [(k, v) for k, v in lines.items() if k > after_line],
        key=lambda t: t[0],
        reverse=True,
    )


# * Shift lines by delta
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


# * Generate edits.json for resume using AI model w/ job description & sections context
def generate_edits(
    resume_lines: Lines, job_text: str, sections_json: str | None, model: str
) -> dict:
    debug_ai(
        f"Starting edit generation - Model: {model}, Resume lines: {len(resume_lines)}, Job text: {len(job_text)} chars"
    )

    # generate edits
    created_at = datetime.now(timezone.utc).isoformat()
    prompt = build_generate_prompt(
        job_text, number_lines(resume_lines), model, created_at, sections_json
    )
    debug_ai(f"Generated generation prompt: {len(prompt)} characters")

    result = run_generate(prompt, model)
    edits = process_ai_response(
        result, model, "generation", log_version_debug=True, log_structure=True
    )

    debug_ai(
        f"Edit generation completed successfully - {len(edits.get('ops', []))} operations generated"
    )
    return edits


# * Generate corrected edits based on validation warnings
def generate_corrected_edits(
    current_edits_json: str,
    resume_lines: Lines,
    job_text: str,
    sections_json: str | None,
    model: str,
    validation_warnings: List[str],
) -> dict:
    debug_ai(
        f"Starting edit correction - Model: {model}, Warnings: {len(validation_warnings)}"
    )

    created_at = datetime.now(timezone.utc).isoformat()
    prompt = build_edit_prompt(
        job_text,
        number_lines(resume_lines),
        current_edits_json,
        validation_warnings,
        model,
        created_at,
        sections_json,
    )
    debug_ai(f"Generated correction prompt: {len(prompt)} characters")

    result = run_generate(prompt, model)
    edits = process_ai_response(result, model, "correction")

    debug_ai(
        f"Edit correction completed successfully - {len(edits.get('ops', []))} operations generated"
    )
    return edits


# * Process MODIFY operation w/ user-modified content
def process_modify_operation(edit_op: EditOperation) -> EditOperation:
    debug_ai(
        f"Processing MODIFY operation for {edit_op.operation} at line {edit_op.line_number}"
    )

    # validate content exists (already updated by interactive UI)
    if not edit_op.content:
        raise EditError("MODIFY operation requires content to be set")
    debug_ai(
        f"MODIFY operation processed - content contains {len(edit_op.content)} characters"
    )

    return edit_op


# * Process PROMPT operation w/ user instruction & AI generation
def process_prompt_operation(
    edit_op: EditOperation,
    resume_lines: Lines,
    job_text: str,
    sections_json: str | None,
    model: str,
) -> EditOperation:
    debug_ai(
        f"Processing PROMPT operation for {edit_op.operation} at line {edit_op.line_number} with model {model}"
    )

    if edit_op.prompt_instruction is None:
        raise EditError("PROMPT operation requires prompt_instruction to be set")

    # build operation context for the prompt
    context_lines = []

    # add operation context
    if edit_op.operation == "replace_line":
        context_lines.append(
            f"Original line {edit_op.line_number}: {edit_op.original_content}"
        )
    elif edit_op.operation == "replace_range":
        context_lines.append(
            f"Original lines {edit_op.start_line}-{edit_op.end_line}: {edit_op.original_content}"
        )
    elif edit_op.operation == "insert_after":
        context_lines.append(f"Inserting after line {edit_op.line_number}")
    elif edit_op.operation == "delete_range":
        context_lines.append(
            f"Deleting lines {edit_op.start_line}-{edit_op.end_line}: {edit_op.original_content}"
        )

    # add surrounding context
    if edit_op.before_context:
        context_lines.append(f"Context before: {' | '.join(edit_op.before_context)}")
    if edit_op.after_context:
        context_lines.append(f"Context after: {' | '.join(edit_op.after_context)}")

    operation_context = "\n".join(context_lines)

    # build AI prompt using dedicated template
    created_at = datetime.now(timezone.utc).isoformat()
    prompt = build_prompt_operation_prompt(
        user_instruction=edit_op.prompt_instruction,
        operation_type=edit_op.operation,
        operation_context=operation_context,
        job_text=job_text,
        resume_with_line_numbers=number_lines(resume_lines),
        model=model,
        created_at=created_at,
        sections_json=sections_json,
    )

    debug_ai(f"Generated PROMPT operation prompt: {len(prompt)} characters")

    # call AI to generate new content
    result = run_generate(prompt, model)

    # validate & parse response (require exactly one operation)
    response_data = process_ai_response(
        result, model, "PROMPT operation", require_single_op=True
    )
    debug_ai(
        f"PROMPT operation AI generation successful - received {len(str(response_data))} characters"
    )

    # extract the single regenerated operation
    new_op = response_data["ops"][0]

    # update operation content w/ AI-generated content
    edit_op.content = new_op.get("text", "")

    # update reasoning if provided
    if "why" in new_op:
        edit_op.reasoning = new_op["why"]

    # update confidence if available (set to high since user specifically requested this)
    edit_op.confidence = new_op.get("confidence", 0.9)

    return edit_op


# * Apply edits to resume lines & return new lines dict
def apply_edits(resume_lines: Lines, edits: dict) -> Lines:
    if edits.get("version") != 1:
        raise EditError(f"Unsupported edits version: {edits.get('version')}")

    new_lines = dict(resume_lines)
    ops = edits.get("ops", [])

    # sort ops by line number (descending) to avoid shifting issues
    sorted_ops = sorted(ops, key=lambda op: get_operation_line(op), reverse=True)

    for op in sorted_ops:
        op_type = op["op"]

        # replace single line
        if op_type == OP_REPLACE_LINE:
            line_num = op["line"]
            if not check_line_exists(line_num, new_lines):
                raise EditError(f"Cannot replace line {line_num}: line does not exist")
            new_lines[line_num] = op["text"]

        # replace range of lines
        elif op_type == OP_REPLACE_RANGE:
            start = op["start"]
            end = op["end"]
            text = op["text"]

            # validate range exists
            # align error message w/ tests: explicitly report missing 'end' if out of bounds
            if not check_line_exists(end, new_lines):
                raise EditError(
                    f"Cannot replace range {start}-{end}: line {end} does not exist"
                )
            exists, missing_line = check_range_exists(start, end, new_lines)
            if not exists:
                raise EditError(
                    f"Cannot replace range {start}-{end}: line {missing_line} does not exist"
                )

            text_lines = text.split("\n") if text else [""]
            old_line_count = end - start + 1
            new_line_count = len(text_lines)
            line_diff = new_line_count - old_line_count

            # collect lines after range (uses shared helper)
            lines_to_move = collect_lines_to_move(new_lines, end)

            # for REPLACE_RANGE, we need to: delete lines_to_move, delete range,
            # insert new content, then reinsert lines_to_move at shifted positions
            if line_diff != 0:
                # remove lines that will be moved
                for k, v in lines_to_move:
                    del new_lines[k]

            # remove old lines in the range
            for line_num in range(start, end + 1):
                del new_lines[line_num]

            # insert new lines
            for i, line_text in enumerate(text_lines):
                new_lines[start + i] = line_text

            # reinsert moved lines at new positions
            if line_diff != 0:
                for k, v in lines_to_move:
                    new_lines[k + line_diff] = v

        # insert after ___
        elif op_type == OP_INSERT_AFTER:
            line_num = op["line"]
            text = op["text"]

            if not check_line_exists(line_num, new_lines):
                raise EditError(
                    f"Cannot insert after line {line_num}: line does not exist"
                )

            # shift all lines after insert point (uses shared helpers)
            text_lines = text.split("\n")
            insert_count = len(text_lines)

            lines_to_move = collect_lines_to_move(new_lines, line_num)
            shift_lines(new_lines, lines_to_move, insert_count)

            # insert new lines
            for i, line_text in enumerate(text_lines):
                new_lines[line_num + 1 + i] = line_text

        # delete lines
        elif op_type == OP_DELETE_RANGE:
            start = op["start"]
            end = op["end"]

            # validate range exists
            exists, missing_line = check_range_exists(start, end, new_lines)
            if not exists:
                raise EditError(
                    f"Cannot delete range {start}-{end}: line {missing_line} does not exist"
                )

            delete_count = end - start + 1

            # delete the range
            for line_num in range(start, end + 1):
                del new_lines[line_num]

            # shift everything after 'end' down (uses shared helpers)
            lines_to_move = collect_lines_to_move(new_lines, end)
            shift_lines(new_lines, lines_to_move, -delete_count)

        else:
            raise EditError(f"Unknown operation type: {op_type}")

    return new_lines


# * Generate unified diff b/w two line dicts
def diff_lines(old: Lines, new: Lines) -> str:
    old_list = [f"{i:>4} {old[i]}" for i in sorted(old.keys())]
    new_list = [f"{i:>4} {new[i]}" for i in sorted(new.keys())]

    return "".join(
        difflib.unified_diff(old_list, new_list, fromfile="old", tofile="new")
    )
