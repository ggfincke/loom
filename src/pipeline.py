from typing import Dict, List
from .document import number_lines
import difflib

# type alias
Lines = Dict[int, str]

# generate edits.json for a resume based on job description & optional sections JSON
def generate_edits(resume_lines: Lines, job_text: str, sections_json: str | None, model: str, risk: str = "med") -> dict:
    from .prompts import build_generate_prompt
    from .openai_client import run_generate
    from pathlib import Path
    
    prompt = build_generate_prompt(job_text, number_lines(resume_lines), sections_json)
    edits = run_generate(prompt, model)
    
    # validate response
    if not isinstance(edits, dict):
        raise ValueError("AI response is not a valid JSON object")
    
    if edits.get("version") != 1:
        raise ValueError(f"Invalid or missing version in AI response: {edits.get('version')}")
    
    if "meta" not in edits or "ops" not in edits:
        raise ValueError("AI response missing required 'meta' or 'ops' fields")
    
    # validate edits & write warnings to file
    warnings = validate_edits(edits, resume_lines, risk)
    if warnings:
        Path(".loom").mkdir(exist_ok=True)
        (Path(".loom") / "edits.warnings.txt").write_text("\n".join(warnings), encoding="utf-8")
    
    return edits

# apply edits to resume lines & return new lines dict 
def apply_edits(resume_lines: Lines, edits: dict, risk: str = "med") -> Lines:
    if edits.get("version") != 1:
        raise ValueError(f"Unsupported edits version: {edits.get('version')}")
    
    # validate edits to fail fast on serious issues
    warnings = validate_edits(edits, resume_lines, risk)
    if warnings:
        # treat warnings as fatal errors for apply
        raise ValueError(f"Validation failed: {'; '.join(warnings)}")
    
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
                raise ValueError(f"Cannot replace line {line_num}: line does not exist")
            new_lines[line_num] = op["text"]
            
        # replace range of lines
        elif op_type == "replace_range":
            start = op["start"]
            end = op["end"]
            text = op["text"]
            
            # validate range exists
            for line_num in range(start, end + 1):
                if line_num not in new_lines:
                    raise ValueError(f"Cannot replace range {start}-{end}: line {line_num} does not exist")
            
            # remove old lines
            for line_num in range(start, end + 1):
                del new_lines[line_num]
            
            # insert new lines
            text_lines = text.split("\n")
            for i, line_text in enumerate(text_lines):
                new_lines[start + i] = line_text
                
        # insert after ___
        elif op_type == "insert_after":
            line_num = op["line"]
            text = op["text"]
            
            if line_num not in new_lines:
                raise ValueError(f"Cannot insert after line {line_num}: line does not exist")
            
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
                    raise ValueError(f"Cannot delete range {start}-{end}: line {line_num} does not exist")
            
            # delete lines
            for line_num in range(start, end + 1):
                del new_lines[line_num]
                
        else:
            raise ValueError(f"Unknown operation type: {op_type}")
    
    return new_lines

# generate unified diff b/w two line dicts
def diff_lines(old: Lines, new: Lines) -> str:    
    old_list = [f"{i:>4} {old[i]}" for i in sorted(old.keys())]
    new_list = [f"{i:>4} {new[i]}" for i in sorted(new.keys())]
    
    return "".join(difflib.unified_diff(old_list, new_list, fromfile="old", tofile="new"))

# validate edits.json structure and ops
def validate_edits(edits: dict, resume_lines: Lines, risk: str) -> List[str]:
    warnings = []
    
    # check ops exists and is non-empty list
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
        
        # validate each op type and required fields
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
            text_line_count = len(op["text"].splitlines())
            range_line_count = end - start + 1
            if text_line_count != range_line_count:
                msg = f"Op {i}: replace_range line count mismatch ({range_line_count} -> {text_line_count})"
                if risk in ["med", "high", "strict"]:
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
    
    return warnings

# get primary line num for an operation
def _get_op_line(op: dict) -> int:
    if "line" in op:
        return op["line"]
    elif "start" in op:
        return op["start"]
    else:
        return 0