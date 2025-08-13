# src/core/pipeline.py
# Core processing pipeline for edit generation, validation, & application

from typing import List, Callable, Optional, Any
from dataclasses import dataclass
from ..loom_io import number_lines
import difflib
import sys
import json
from datetime import datetime, timezone
from ..config.settings import LoomSettings
from .exceptions import ValidationError, AIError, EditError
from ..loom_io.console import console

from ..loom_io.types import Lines

# validation result for state machine transitions
@dataclass
class ValidationResult:
    is_complete: bool
    value: Any = None
    next_state: str = ""
    result: Any = None

# validation state machine for handling edit validation errors
class ValidationStateMachine:
    def __init__(self, settings: LoomSettings, initial_policy: str = "ask", ui=None):
        self.settings = settings
        self.state = self._normalize_policy(initial_policy)
        self.ui = ui or self._get_fallback_ui()
        self.transitions = {
            'ask': self._handle_ask,
            'retry': self._handle_retry,
            'manual': self._handle_manual,
            'fail_soft': self._handle_fail_soft,
            'fail_hard': self._handle_fail_hard,
        }
    
    # create fallback UI when none provided
    def _get_fallback_ui(self):
        from ..loom_io.ui import UI
        return UI(progress=None)
    
    # normalize initial policy to standard values
    def _normalize_policy(self, policy: str) -> str:
        policy = (policy or "ask").strip().lower()
        if policy in ("fail", "fail:soft"):
            return "fail_soft"
        elif policy == "fail:hard":
            return "fail_hard"
        return policy
    
    # main validation loop with state transitions
    def process(self, validate_fn: Callable[[], List[str]], edit_fn: Optional[Callable[[List[str]], Any]] = None) -> Any:
        result = None
        
        while True:
            warnings = validate_fn()
            
            if not warnings:
                return result if result is not None else True
            
            self.settings.loom_dir.mkdir(exist_ok=True)
            self.settings.warnings_path.write_text("\n".join(warnings), encoding="utf-8")
            
            handler = self.transitions.get(self.state, self._handle_ask)
            validation_result = handler(warnings, validate_fn, edit_fn)
            
            if validation_result.is_complete:
                return validation_result.value
            
            self.state = validation_result.next_state
            if validation_result.result is not None:
                result = validation_result.result
    
    # interactive prompt for user to choose validation policy
    def _handle_ask(self, warnings: List[str], validate_fn: Callable[[], List[str]], edit_fn: Optional[Callable[[List[str]], Any]]) -> ValidationResult:
        if not sys.stdin.isatty():
            error_warnings = ["Validation failed (ask not possible - non-interactive):"] + warnings
            raise ValidationError(error_warnings, recoverable=False)
        
        # Print a blank line to separate from any progress output
        self.ui.print()
        self.ui.print("⚠️  Validation errors found:")
        for warning in warnings:
            self.ui.print(f"   {warning}")
        
        while True:
            self.ui.print()  # Ensure clean line before prompt
            choice = self.ui.ask("Choose: [bold white](f)[/]ail-soft, [bold white](h)[/]ard-fail, [bold white](m)[/]anual, [bold white](r)[/]etry: ").lower().strip()
            
            if choice in ['f', 'fail', 'fail:soft']:
                return ValidationResult(is_complete=False, next_state="fail_soft")
            elif choice in ['h', 'hard', 'fail:hard']:
                return ValidationResult(is_complete=False, next_state="fail_hard")
            elif choice in ['m', 'manual']:
                return ValidationResult(is_complete=False, next_state="manual")
            elif choice in ['r', 'retry']:
                return ValidationResult(is_complete=False, next_state="retry")
            else:
                self.ui.print("Invalid choice. Please enter f, h, m, or r.")

    # attempt to regenerate edits with AI correction
    def _handle_retry(self, warnings: List[str], validate_fn: Callable[[], List[str]], edit_fn: Optional[Callable[[List[str]], Any]]) -> ValidationResult:
        if edit_fn is None:
            self.ui.print("❌ Retry not available (no edit function provided)")
            self.ui.print("Falling back to manual mode...")
            return ValidationResult(is_complete=False, next_state="manual")
        
        try:
            result = edit_fn(warnings)
            self.settings.edits_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            self.ui.print("✅ Generated corrected edits, re-validating...")
            return ValidationResult(is_complete=False, next_state="ask", result=result)
        except Exception as e:
            self.ui.print(f"❌ Error generating corrected edits: {e}")
            self.ui.print("Falling back to manual mode...")
            return ValidationResult(is_complete=False, next_state="manual")
    
    # wait for user to manually edit the edits.json file
    def _handle_manual(self, warnings: List[str], validate_fn: Callable[[], List[str]], edit_fn: Optional[Callable[[List[str]], Any]]) -> ValidationResult:
        if not sys.stdin.isatty():
            error_warnings = ["Manual mode not available (not a TTY):"] + warnings
            raise ValidationError(error_warnings, recoverable=False)
        
        self.ui.print(f"⚠️  Validation errors found. Please edit {self.settings.edits_path} manually:")
        for warning in warnings:
            self.ui.print(f"   {warning}")
        
        edits_path = self.settings.edits_path
        while True:
            self.ui.ask("Press Enter after editing edits.json to re-validate...")
            
            if not edits_path.exists():
                self.ui.print(f"❌ {self.settings.edits_path} not found")
                continue
                
            try:
                json.loads(edits_path.read_text(encoding="utf-8"))
                self.ui.print("✅ File edited, re-validating...")
                return ValidationResult(is_complete=False, next_state="manual")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                self.ui.print(f"❌ Error reading edits.json: {e}")
                continue
    
    # raise validation error & exit
    def _handle_fail_soft(self, warnings: List[str], validate_fn: Callable[[], List[str]], edit_fn: Optional[Callable[[List[str]], Any]]) -> ValidationResult:
        raise ValidationError(warnings, recoverable=False)
    
    # raise validation error with hard failure message
    def _handle_fail_hard(self, warnings: List[str], validate_fn: Callable[[], List[str]], edit_fn: Optional[Callable[[List[str]], Any]]) -> ValidationResult:
        error_warnings = ["Validation failed (hard):"] + warnings
        raise ValidationError(error_warnings, recoverable=False)

# handle validation errors based on policy
def handle_validation_error(settings: LoomSettings,
                           validate_fn: Callable[[], List[str]], 
                           on_error: str = "ask",
                           edit_fn: Optional[Callable[[List[str]], Any]] = None,
                           ui=None) -> Any:
    state_machine = ValidationStateMachine(settings, on_error, ui)
    return state_machine.process(validate_fn, edit_fn)

# generate edits.json for a resume based on job description & optional sections JSON
def generate_edits(settings: LoomSettings, resume_lines: Lines, job_text: str, sections_json: str | None, model: str, risk: str = "med", on_error: str = "ask", ui=None) -> dict:
    from ..ai.prompts import build_generate_prompt
    from ..ai.clients.openai_client import run_generate
    
    # edits
    edits: Optional[dict] = None
    
    def create_edits():
        nonlocal edits
        created_at = datetime.now(timezone.utc).isoformat()
        prompt = build_generate_prompt(job_text, number_lines(resume_lines), model, created_at, sections_json)
        result = run_generate(prompt, model)
        
        # handle JSON parsing errors - don't crash, let validation system handle it
        if not result.success:
            # return a special failure object that validation can detect
            edits = {
                "_json_parse_error": True,
                "_error_details": result.error,
                "_raw_response": result.raw_text,
                "_json_text": result.json_text,
                "version": 1, 
                "meta": {},
                "ops": []
            }
            return edits
        
        edits = result.data
        
        # validate response structure
        if not isinstance(edits, dict):
            raise AIError("AI response is not a valid JSON object")
        
        if edits.get("version") != 1:
            raise AIError(f"Invalid or missing version in AI response: {edits.get('version')}")
        
        if "meta" not in edits or "ops" not in edits:
            raise AIError("AI response missing required 'meta' or 'ops' fields")
            
        return edits
    
    def edit_edits(validation_warnings):
        # read current edits from file
        if settings.edits_path.exists():
            current_edits_json = settings.edits_path.read_text(encoding="utf-8")
        else:
            raise EditError("No existing edits file found for correction")
        
        from ..ai.prompts import build_edit_prompt
        created_at = datetime.now(timezone.utc).isoformat()
        prompt = build_edit_prompt(job_text, number_lines(resume_lines), current_edits_json, validation_warnings, model, created_at, sections_json)
        result = run_generate(prompt, model)
        
        # handle JSON parsing errors - don't crash, let validation system handle it
        if not result.success:
            # return a special failure object that validation can detect
            edits = {
                "_json_parse_error": True,
                "_error_details": result.error,
                "_raw_response": result.raw_text,
                "_json_text": result.json_text,
                "version": 1,
                "meta": {},
                "ops": []
            }
            return edits
        
        edits = result.data
        
        # validate response structure
        if not isinstance(edits, dict):
            raise AIError("AI response is not a valid JSON object")
        
        if edits.get("version") != 1:
            raise AIError(f"Invalid or missing version in AI response: {edits.get('version')}")
        
        if "meta" not in edits or "ops" not in edits:
            raise AIError("AI response missing required 'meta' or 'ops' fields")
            
        return edits
    
    # initial generation
    edits = create_edits()
    
    # immediately persist edits so manual mode has a file to work with
    settings.loom_dir.mkdir(exist_ok=True)
    settings.edits_path.write_text(json.dumps(edits, indent=2), encoding="utf-8")
    
    # validate with a closure that can be updated
    current_edits = [edits]  # use list to make it mutable in closure
    
    def validate_current():
        return validate_edits(current_edits[0], resume_lines, risk) if current_edits[0] is not None else ["Edits not initialized"]
    
    def edit_edits_and_update(validation_warnings):
        # call the original edit function
        new_edits = edit_edits(validation_warnings)
        # update the current edits being validated
        current_edits[0] = new_edits
        return new_edits
    
    # validate
    result = handle_validation_error(
        settings,
        validate_fn=validate_current,
        on_error=on_error,
        edit_fn=edit_edits_and_update,
        ui=ui,
    )
    
    # if result, there was a regeneration
    if isinstance(result, dict):
        edits = result
    elif edits is None:
        raise EditError("Failed to generate valid edits")
    
    return edits

# apply edits to resume lines & return new lines dict 
def apply_edits(settings: LoomSettings, resume_lines: Lines, edits: dict, risk: str = "med", on_error: str = "ask", ui=None) -> Lines:
    if edits.get("version") != 1:
        raise EditError(f"Unsupported edits version: {edits.get('version')}")
    
    # pre-apply validation
    handle_validation_error(settings, lambda: validate_edits(edits, resume_lines, risk), on_error, ui=ui)
    
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

# generate unified diff b/w two line dicts
def diff_lines(old: Lines, new: Lines) -> str:    
    old_list = [f"{i:>4} {old[i]}" for i in sorted(old.keys())]
    new_list = [f"{i:>4} {new[i]}" for i in sorted(new.keys())]
    
    return "".join(difflib.unified_diff(old_list, new_list, fromfile="old", tofile="new"))

# validate edits.json structure & ops
def validate_edits(edits: dict, resume_lines: Lines, risk: str) -> List[str]:
    warnings = []
    
    # check for JSON parsing errors first
    if edits.get("_json_parse_error"):
        error_details = edits.get("_error_details", "Unknown JSON error")
        raw_response = edits.get("_raw_response", "")
        json_text = edits.get("_json_text", "")
        
        warnings.append(f"AI returned invalid JSON: {error_details}")
        if raw_response:
            warnings.append(f"Raw AI response (first 500 chars): {raw_response[:500]}...")
        if json_text:
            warnings.append(f"Extracted JSON (first 500 chars): {json_text[:500]}...")
        warnings.append("You can manually edit the JSON file or retry with AI correction")
        return warnings
    
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


# pipeline class with dependency injection
class Pipeline:
    # main processing pipeline with injected settings dependency
    
    def __init__(self, settings: LoomSettings):
        self.settings = settings
    
    def generate_edits(self, resume_lines: Lines, job_text: str, sections_json: str | None, model: str, risk: str = "med", on_error: str = "ask", ui=None) -> dict:
        # generate edits.json for a resume based on job description & optional sections JSON
        return generate_edits(self.settings, resume_lines, job_text, sections_json, model, risk, on_error, ui)
    
    def apply_edits(self, resume_lines: Lines, edits: dict, risk: str = "med", on_error: str = "ask", ui=None) -> Lines:
        # apply edits to resume lines & return new lines dict
        return apply_edits(self.settings, resume_lines, edits, risk, on_error, ui)
    
    def diff_lines(self, old: Lines, new: Lines) -> str:
        # generate unified diff between two line dicts
        return diff_lines(old, new)
    
    def validate_edits(self, edits: dict, resume_lines: Lines, risk: str) -> List[str]:
        # validate edits.json structure & operations
        return validate_edits(edits, resume_lines, risk)