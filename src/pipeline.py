from typing import Dict
from .document import number_lines
import difflib

# type alias
Lines = Dict[int, str]

# generate edits.json for a resume based on job description & optional sections JSON
def generate_edits(resume_lines: Lines, job_text: str, sections_json: str | None, model: str) -> dict:
    from .prompts import build_generate_prompt
    from .openai_client import run_generate
    
    prompt = build_generate_prompt(job_text, number_lines(resume_lines), sections_json)
    edits = run_generate(prompt, model)
    
    # validate response
    if not isinstance(edits, dict):
        raise ValueError("AI response is not a valid JSON object")
    
    if edits.get("version") != 1:
        raise ValueError(f"Invalid or missing version in AI response: {edits.get('version')}")
    
    if "meta" not in edits or "ops" not in edits:
        raise ValueError("AI response missing required 'meta' or 'ops' fields")
    
    return edits

# apply edits to resume lines & return new lines dict 
def apply_edits(resume_lines: Lines, edits: dict) -> Lines:
    if edits.get("version") != 1:
        raise ValueError(f"Unsupported edits version: {edits.get('version')}")
    
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
            
            # find highest line num to determine where to insert 
            max_line = max(new_lines.keys())
            
            # shift all lines after insert point
            text_lines = text.split("\n")
            insert_count = len(text_lines)
            
            # move existing lines
            lines_to_move = [(k, v) for k, v in new_lines.items() if k > line_num]
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
    
    return "".join(difflib.unified_diff(
        old_list, new_list,
        fromfile="old",
        tofile="new",
        lineterm=""
    ))

# get primary line num for an operation
def _get_op_line(op: dict) -> int:
    if "line" in op:
        return op["line"]
    elif "start" in op:
        return op["start"]
    else:
        return 0