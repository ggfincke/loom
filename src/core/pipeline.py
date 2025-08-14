# src/core/pipeline.py
# Core processing pipeline for edit generation, validation, & application

from typing import List
from ..loom_io import number_lines
import difflib
import json
from datetime import datetime, timezone
from .exceptions import AIError, EditError, JSONParsingError
from .constants import RiskLevel
from ..ai.prompts import build_generate_prompt, build_edit_prompt
from ..ai.clients.openai_client import run_generate

from ..loom_io.types import Lines

# * Generate edits.json for resume using AI model w/ job description & sections context
def generate_edits(resume_lines: Lines, job_text: str, sections_json: str | None, model: str) -> dict:
    
    # generate edits
    created_at = datetime.now(timezone.utc).isoformat()
    prompt = build_generate_prompt(job_text, number_lines(resume_lines), model, created_at, sections_json)
    result = run_generate(prompt, model)
    
    # handle JSON parsing errors
    if not result.success:
        # create a trimmed snippet from problematic JSON
        lines = result.json_text.split('\n')
        if len(lines) > 5:
            snippet = '\n'.join(lines[:5]) + '\n...'
        else:
            snippet = result.json_text
        raise JSONParsingError(f"AI generated invalid JSON:\n{snippet}\nError: {result.error}")
    
    edits = result.data
    
    # validate response structure
    if not isinstance(edits, dict):
        raise AIError("AI response is not a valid JSON object")
    
    if edits.get("version") != 1:
        raise AIError(f"Invalid or missing version in AI response: {edits.get('version')}")
    
    if "meta" not in edits or "ops" not in edits:
        raise AIError("AI response missing required 'meta' or 'ops' fields")
        
    return edits

# * Generate corrected edits based on validation warnings
def generate_corrected_edits(current_edits_json: str, resume_lines: Lines, job_text: str, sections_json: str | None, model: str, validation_warnings: List[str]) -> dict:
    
    
    created_at = datetime.now(timezone.utc).isoformat()
    prompt = build_edit_prompt(job_text, number_lines(resume_lines), current_edits_json, validation_warnings, model, created_at, sections_json)
    
    result = run_generate(prompt, model)
    
    # handle JSON parsing errors
    if not result.success:
        # create a trimmed snippet from problematic JSON
        lines = result.json_text.split('\n')
        if len(lines) > 5:
            snippet = '\n'.join(lines[:5]) + '\n...'
        else:
            snippet = result.json_text
        raise JSONParsingError(f"AI generated invalid JSON during correction:\n{snippet}\nError: {result.error}")
    
    edits = result.data
    
    # validate response structure
    if not isinstance(edits, dict):
        raise AIError("AI response is not a valid JSON object")
    
    if edits.get("version") != 1:
        raise AIError(f"Invalid or missing version in AI response: {edits.get('version')}")
    
    if "meta" not in edits or "ops" not in edits:
        raise AIError("AI response missing required 'meta' or 'ops' fields")
        
    return edits

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
            
            # reinsert moved lines with new positions
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

# * Validate edits.json structure & ops
def validate_edits(edits: dict, resume_lines: Lines, risk: RiskLevel) -> List[str]:
    warnings = []
    
    # check ops exists & is non-empty list
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
    
    # track line usage to detect conflicts
    line_usage = {}
    
    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            warnings.append(f"Op {i}: must be an object")
            continue
        
        op_type = op.get("op")
        if not op_type:
            warnings.append(f"Op {i}: missing 'op' field")
            continue
        
        # validate each op type & required fields
        if op_type == "replace_line":
            if "line" not in op:
                warnings.append(f"Op {i}: replace_line missing 'line' field")
                continue
            if "text" not in op:
                warnings.append(f"Op {i}: replace_line missing 'text' field")
                continue
            
            line = op["line"]
            if not isinstance(line, int) or line < 1:
                warnings.append(f"Op {i}: 'line' must be integer >= 1")
                continue
            
            if not isinstance(op["text"], str):
                warnings.append(f"Op {i}: 'text' must be string")
                continue
            
            # block multiline replace_line operations
            if "\n" in op["text"]:
                warnings.append(f"Op {i}: replace_line text contains newline; use replace_range")
                continue
            
            # check line bounds
            if line not in resume_lines:
                warnings.append(f"Op {i}: line {line} not in resume bounds")
                continue
                
            # check for conflicts
            if line in line_usage:
                warnings.append(f"Op {i}: duplicate operation on line {line}")
            line_usage[line] = op_type
        
        elif op_type == "replace_range":
            if "start" not in op or "end" not in op or "text" not in op:
                warnings.append(f"Op {i}: replace_range missing required fields (start, end, text)")
                continue
            
            start, end = op["start"], op["end"]
            if not isinstance(start, int) or not isinstance(end, int):
                warnings.append(f"Op {i}: start and end must be integers")
                continue
            
            if start < 1 or end < 1 or start > end:
                warnings.append(f"Op {i}: invalid range {start}-{end}")
                continue
            
            if not isinstance(op["text"], str):
                warnings.append(f"Op {i}: 'text' must be string")
                continue
            
            # check line bounds
            for line in range(start, end + 1):
                if line not in resume_lines:
                    warnings.append(f"Op {i}: line {line} not in resume bounds")
                    break
            
            # validate line count mismatch in replace_range
            # use split("\n") instead of splitlines() to handle empty strings correctly
            if op["text"]:
                text_line_count = len(op["text"].split("\n"))
            else:
                # empty text is treated as single line
                text_line_count = 1  
            range_line_count = end - start + 1
            if text_line_count != range_line_count:
                msg = f"Op {i}: replace_range line count mismatch ({range_line_count} -> {text_line_count})"
                if risk in [RiskLevel.MED, RiskLevel.HIGH, RiskLevel.STRICT]:
                    warnings.append(msg + " (will cause line collisions)")
                else:
                    warnings.append(msg)
            
            # check for conflicts in range
            for line in range(start, end + 1):
                if line in line_usage:
                    warnings.append(f"Op {i}: duplicate operation on line {line}")
                    break
            for line in range(start, end + 1):
                line_usage[line] = op_type
        
        elif op_type == "insert_after":
            if "line" not in op or "text" not in op:
                warnings.append(f"Op {i}: insert_after missing required fields (line, text)")
                continue
            
            line = op["line"]
            if not isinstance(line, int) or line < 1:
                warnings.append(f"Op {i}: 'line' must be integer >= 1")
                continue
            
            if not isinstance(op["text"], str):
                warnings.append(f"Op {i}: 'text' must be string")
                continue
            
            # check line bounds
            if line not in resume_lines:
                warnings.append(f"Op {i}: line {line} not in resume bounds")
                continue
        
        elif op_type == "delete_range":
            if "start" not in op or "end" not in op:
                warnings.append(f"Op {i}: delete_range missing required fields (start, end)")
                continue
            
            start, end = op["start"], op["end"]
            if not isinstance(start, int) or not isinstance(end, int):
                warnings.append(f"Op {i}: start and end must be integers")
                continue
            
            if start < 1 or end < 1 or start > end:
                warnings.append(f"Op {i}: invalid range {start}-{end}")
                continue
            
            # check line bounds
            for line in range(start, end + 1):
                if line not in resume_lines:
                    warnings.append(f"Op {i}: line {line} not in resume bounds")
                    break
            
            # check for conflicts in range
            for line in range(start, end + 1):
                if line in line_usage:
                    warnings.append(f"Op {i}: duplicate operation on line {line}")
                    break
            for line in range(start, end + 1):
                line_usage[line] = op_type
        
        else:
            warnings.append(f"Op {i}: unknown operation type '{op_type}'")
    
    # detect cross-op conflicts: insert_after on a line later deleted
    delete_ranges = [(op["start"], op["end"]) for op in ops if op.get("op") == "delete_range"]
    for i, op in enumerate(ops):
        if op.get("op") == "insert_after":
            ln = op["line"]
            if any(s <= ln <= e for s, e in delete_ranges):
                warnings.append(f"Op {i}: insert_after on line {ln} that is deleted by a delete_range")
    
    # detect overlaps between delete_range & replace_range
    replace_ranges = [(op["start"], op["end"]) for op in ops if op.get("op") == "replace_range"]
    for i, op in enumerate(ops):
        if op.get("op") == "delete_range":
            s, e = op["start"], op["end"]
            if any(not (e2 < s or s2 > e) for (s2, e2) in replace_ranges):
                warnings.append(f"Op {i}: delete_range overlaps a replace_range; split or reorder ops")
    
    # detect multiple insert_after on the same line
    seen_inserts = set()
    for i, op in enumerate(ops):
        if op.get("op") == "insert_after":
            ln = op["line"]
            if ln in seen_inserts:
                warnings.append(f"Op {i}: multiple insert_after on line {ln}")
            seen_inserts.add(ln)
    
    return warnings

# get primary line num for an operation
def _get_op_line(op: dict) -> int:
    if "line" in op:
        return op["line"]
    elif "start" in op:
        return op["start"]
    else:
        return 0


