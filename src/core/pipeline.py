# src/core/pipeline.py
# Core processing pipeline for edit generation, validation, & application

from typing import List
import difflib
from datetime import datetime, timezone
from .exceptions import AIError, EditError, JSONParsingError
from ..ai.prompts import build_generate_prompt, build_edit_prompt, build_prompt_operation_prompt
from ..ai.clients import run_generate

from ..loom_io.types import Lines
from .constants import EditOperation
from .debug import debug_ai, debug_error

# * Generate edits.json for resume using AI model w/ job description & sections context
def generate_edits(resume_lines: Lines, job_text: str, sections_json: str | None, model: str) -> dict:
    debug_ai(f"Starting edit generation - Model: {model}, Resume lines: {len(resume_lines)}, Job text: {len(job_text)} chars")
    
    # generate edits
    created_at = datetime.now(timezone.utc).isoformat()
    prompt = build_generate_prompt(job_text, number_lines(resume_lines), model, created_at, sections_json)
    debug_ai(f"Generated prompt: {len(prompt)} characters")
    
    result = run_generate(prompt, model)
    
    # handle JSON parsing errors
    if not result.success:
        debug_error(Exception(result.error), f"AI generation failed for model {model}")
        # create a trimmed snippet from problematic JSON
        lines = result.json_text.split('\n') if result.json_text else []
        if len(lines) > 5:
            snippet = '\n'.join(lines[:5]) + '\n...'
        else:
            snippet = result.json_text
        error_msg = f"AI generated invalid JSON using model '{model}':\n{snippet}\nError: {result.error}"
        if result.raw_text and result.raw_text != result.json_text:
            error_msg += f"\nFull raw response: {result.raw_text[:300]}{'...' if len(result.raw_text) > 300 else ''}"
        raise JSONParsingError(error_msg)
    
    edits = result.data
    debug_ai(f"AI generation successful - received {len(str(edits))} chars of JSON data")
    debug_ai(f"JSON structure: {list(edits.keys()) if isinstance(edits, dict) else type(edits).__name__}")
    
    # validate response structure
    if not isinstance(edits, dict):
        raise AIError(f"AI response is not a valid JSON object (got {type(edits).__name__}) for model '{model}'")
    
    if edits.get("version") != 1:
        debug_ai(f"Full JSON response: {str(edits)[:500]}{'...' if len(str(edits)) > 500 else ''}")
        raise AIError(f"Invalid or missing version in AI response: {edits.get('version')} (expected 1) for model '{model}'")
    
    if "meta" not in edits or "ops" not in edits:
        missing_fields = []
        if "meta" not in edits:
            missing_fields.append("meta")
        if "ops" not in edits:
            missing_fields.append("ops")
        raise AIError(f"AI response missing required fields: {', '.join(missing_fields)} for model '{model}'")
    
    debug_ai(f"Edit generation completed successfully - {len(edits.get('ops', []))} operations generated")
    return edits

# * Generate corrected edits based on validation warnings
def generate_corrected_edits(current_edits_json: str, resume_lines: Lines, job_text: str, sections_json: str | None, model: str, validation_warnings: List[str]) -> dict:
    debug_ai(f"Starting edit correction - Model: {model}, Warnings: {len(validation_warnings)}")
    
    created_at = datetime.now(timezone.utc).isoformat()
    prompt = build_edit_prompt(job_text, number_lines(resume_lines), current_edits_json, validation_warnings, model, created_at, sections_json)
    debug_ai(f"Generated correction prompt: {len(prompt)} characters")
    
    result = run_generate(prompt, model)
    
    # handle JSON parsing errors
    if not result.success:
        debug_error(Exception(result.error), f"AI correction failed for model {model}")
        # create a trimmed snippet from problematic JSON
        lines = result.json_text.split('\n') if result.json_text else []
        if len(lines) > 5:
            snippet = '\n'.join(lines[:5]) + '\n...'
        else:
            snippet = result.json_text
        error_msg = f"AI generated invalid JSON during correction using model '{model}':\n{snippet}\nError: {result.error}"
        if result.raw_text and result.raw_text != result.json_text:
            error_msg += f"\nFull raw response: {result.raw_text[:300]}{'...' if len(result.raw_text) > 300 else ''}"
        raise JSONParsingError(error_msg)
    
    edits = result.data
    debug_ai(f"AI correction successful - received {len(str(edits))} chars of JSON data")
    
    # validate response structure
    if not isinstance(edits, dict):
        raise AIError(f"AI response is not a valid JSON object (got {type(edits).__name__}) during correction for model '{model}'")
    
    if edits.get("version") != 1:
        raise AIError(f"Invalid or missing version in AI response: {edits.get('version')} (expected 1) during correction for model '{model}'")
    
    if "meta" not in edits or "ops" not in edits:
        missing_fields = []
        if "meta" not in edits:
            missing_fields.append("meta")
        if "ops" not in edits:
            missing_fields.append("ops")
        raise AIError(f"AI response missing required fields: {', '.join(missing_fields)} during correction for model '{model}'")
    
    debug_ai(f"Edit correction completed successfully - {len(edits.get('ops', []))} operations generated")
    return edits

# * Process MODIFY operation w/ user-modified content
def process_modify_operation(edit_op: EditOperation) -> EditOperation:
    debug_ai(f"Processing MODIFY operation for {edit_op.operation} at line {edit_op.line_number}")
    
    # validate content exists (already updated by interactive UI)
    if not edit_op.content:
        raise EditError("MODIFY operation requires content to be set")
    debug_ai(f"MODIFY operation processed - content contains {len(edit_op.content)} characters")
    
    return edit_op

# * Process PROMPT operation w/ user instruction & AI generation
def process_prompt_operation(edit_op: EditOperation, resume_lines: Lines, job_text: str, sections_json: str | None, model: str) -> EditOperation:
    debug_ai(f"Processing PROMPT operation for {edit_op.operation} at line {edit_op.line_number} with model {model}")
    
    if edit_op.prompt_instruction is None:
        raise EditError("PROMPT operation requires prompt_instruction to be set")
    
    # build operation context for the prompt
    context_lines = []
    
    # add operation context
    if edit_op.operation == "replace_line":
        context_lines.append(f"Original line {edit_op.line_number}: {edit_op.original_content}")
    elif edit_op.operation == "replace_range":
        context_lines.append(f"Original lines {edit_op.start_line}-{edit_op.end_line}: {edit_op.original_content}")
    elif edit_op.operation == "insert_after":
        context_lines.append(f"Inserting after line {edit_op.line_number}")
    elif edit_op.operation == "delete_range":
        context_lines.append(f"Deleting lines {edit_op.start_line}-{edit_op.end_line}: {edit_op.original_content}")
    
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
        sections_json=sections_json
    )
    
    debug_ai(f"Generated PROMPT operation prompt: {len(prompt)} characters")
    
    # call AI to generate new content
    result = run_generate(prompt, model)
    
    if not result.success:
        debug_error(Exception(result.error), f"AI generation failed for PROMPT operation with model {model}")
        raise AIError(f"AI failed to process PROMPT operation: {result.error}")
    
    # parse JSON response containing the regenerated operation
    response_data = result.data
    debug_ai(f"PROMPT operation AI generation successful - received {len(str(response_data))} characters")
    
    # validate response structure
    if not isinstance(response_data, dict):
        raise AIError(f"AI response is not a valid JSON object (got {type(response_data).__name__}) for PROMPT operation")
    
    if response_data.get("version") != 1:
        raise AIError(f"Invalid or missing version in AI response: {response_data.get('version')} (expected 1) for PROMPT operation")
    
    if "ops" not in response_data or not response_data["ops"]:
        raise AIError("AI response missing 'ops' array or ops array is empty for PROMPT operation")
    
    if len(response_data["ops"]) != 1:
        raise AIError(f"AI response must contain exactly one operation, got {len(response_data['ops'])} for PROMPT operation")
    
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
    sorted_ops = sorted(ops, key=lambda op: _get_op_line(op), reverse=True)
    
    for op in sorted_ops:
        op_type = op["op"]
        
        # replace single line
        if op_type == "replace_line":
            line_num = op["line"]
            if line_num not in new_lines:
                raise EditError(f"Cannot replace line {line_num}: line does not exist")
            new_lines[line_num] = op["text"]
            
        # replace range of lines
        elif op_type == "replace_range":
            start = op["start"]
            end = op["end"]
            text = op["text"]
            
            # validate range exists
            # align error message w/ tests: explicitly report missing 'end' if out of bounds
            if end not in new_lines:
                raise EditError(f"Cannot replace range {start}-{end}: line {end} does not exist")
            for line_num in range(start, end + 1):
                if line_num not in new_lines:
                    raise EditError(f"Cannot replace range {start}-{end}: line {line_num} does not exist")
            
            text_lines = text.split("\n") if text else [""]
            old_line_count = end - start + 1
            new_line_count = len(text_lines)
            line_diff = new_line_count - old_line_count
            
            # collect lines that need to be moved (after the replacement range)
            lines_to_move = sorted([(k, v) for k, v in new_lines.items() if k > end], 
                                 key=lambda t: t[0], reverse=True)
            
            # if changing number of lines, need to shift later lines
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
            
            # reinsert moved lines w/ new positions
            if line_diff != 0:
                for k, v in lines_to_move:
                    new_lines[k + line_diff] = v
                
        # insert after ___
        elif op_type == "insert_after":
            line_num = op["line"]
            text = op["text"]
            
            if line_num not in new_lines:
                raise EditError(f"Cannot insert after line {line_num}: line does not exist")
            
            # shift all lines after insert point
            text_lines = text.split("\n")
            insert_count = len(text_lines)
            
            # move existing lines in descending order to avoid collisions
            lines_to_move = sorted([(k, v) for k, v in new_lines.items() if k > line_num], key=lambda t: t[0], reverse=True)
            for k, v in lines_to_move:
                del new_lines[k]
                new_lines[k + insert_count] = v
            
            # insert new lines
            for i, line_text in enumerate(text_lines):
                new_lines[line_num + 1 + i] = line_text
                
        # delete lines
        elif op_type == "delete_range":
            start = op["start"]
            end = op["end"]
            
            # validate range exists
            for line_num in range(start, end + 1):
                if line_num not in new_lines:
                    raise EditError(f"Cannot delete range {start}-{end}: line {line_num} does not exist")
            
            delete_count = end - start + 1
            
            # delete the range
            for line_num in range(start, end + 1):
                del new_lines[line_num]
            
            # shift everything after 'end' down
            lines_to_move = sorted([(k, v) for k, v in new_lines.items() if k > end], key=lambda t: t[0])
            for k, v in lines_to_move:
                del new_lines[k]
                new_lines[k - delete_count] = v
                
        else:
            raise EditError(f"Unknown operation type: {op_type}")
    
    return new_lines

# * Generate unified diff b/w two line dicts
def diff_lines(old: Lines, new: Lines) -> str:
    old_list = [f"{i:>4} {old[i]}" for i in sorted(old.keys())]
    new_list = [f"{i:>4} {new[i]}" for i in sorted(new.keys())]
    
    return "".join(difflib.unified_diff(old_list, new_list, fromfile="old", tofile="new"))


# * Get primary line number for operation
def _get_op_line(op: dict) -> int:
    if "line" in op:
        return op["line"]
    elif "start" in op:
        return op["start"]
    else:
        return 0

# ! Moved from loom_io.documents to avoid circular imports
# * Number lines in resume
def number_lines(resume: Lines) -> str:
    return "\n".join(f"{i:>4} {text}" for i, text in sorted(resume.items()))
