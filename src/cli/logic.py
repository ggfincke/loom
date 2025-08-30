# src/cli/logic.py
# CLI-layer logic wrappers & argument resolution

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, Any

from ..config.settings import LoomSettings
from ..loom_io.generics import ensure_parent
from ..loom_io.types import Lines
from ..core.constants import RiskLevel, ValidationPolicy, EditOperation, DiffOp
from ..core.pipeline import (
    generate_edits,
    generate_corrected_edits,
    apply_edits,
    process_modify_operation,
    process_prompt_operation,
)
from ..core.validation import validate_edits
from ..core.exceptions import EditError, JSONParsingError
from ..core.validation import handle_validation_error
from ..ui.diff_resolution.diff_display import main_display_loop


def _resolve(provided_value: Any, settings_default: Any) -> Any:
    return settings_default if provided_value is None else provided_value


class OptionsResolved(TypedDict):
    risk: RiskLevel
    on_error: ValidationPolicy


# * Resolve CLI arguments using settings defaults when values are not provided
class ArgResolver:

    def __init__(self, settings: LoomSettings):
        self.settings = settings

    def resolve_common(self, **kwargs) -> dict:
        return {
            "resume": _resolve(kwargs.get("resume"), self.settings.resume_path),
            "job": _resolve(kwargs.get("job"), self.settings.job_path),
            "model": _resolve(kwargs.get("model"), self.settings.model),
            "sections_path": _resolve(
                kwargs.get("sections_path"), self.settings.sections_path
            ),
            "edits_json": _resolve(
                kwargs.get("edits_json"), self.settings.edits_path
            ),
            "out_json": _resolve(
                kwargs.get("out_json"), self.settings.sections_path
            ),
        }

    def resolve_paths(self, **kwargs) -> dict:
        return {
            "output_resume": _resolve(
                kwargs.get("output_resume"),
                Path(self.settings.output_dir) / "tailored_resume.docx",
            ),
        }

    def resolve_options(self, **kwargs) -> OptionsResolved:
        return {
            "risk": _resolve(kwargs.get("risk"), RiskLevel.MED),
            "on_error": _resolve(kwargs.get("on_error"), ValidationPolicy.ASK),
        }


# * Generate & validate edits; persist intermediate edits to disk for manual flows
def generate_edits_core(
    settings: LoomSettings,
    resume_lines: Lines,
    job_text: str,
    sections_json: str | None,
    model: str,
    risk: RiskLevel,
    policy: ValidationPolicy,
    ui,
    persist_path: Path | None = None,
) -> dict | None:
    # create initial edits using AI
    json_error_warning = None
    try:
        edits = generate_edits(
            resume_lines=resume_lines, job_text=job_text, sections_json=sections_json, model=model
        )
    except JSONParsingError as e:
        # convert JSON parsing error to validation warnings for interactive handling
        json_error_warning = str(e)
        edits = None

    # persist edits or create placeholder for manual editing
    target_path = persist_path if persist_path is not None else settings.edits_path
    ensure_parent(target_path)
    
    if edits is not None:
        # persist successful edits
        target_path.write_text(json.dumps(edits, indent=2), encoding="utf-8")
    else:
        # create placeholder edits file for manual editing when JSON parsing fails
        placeholder_edits = {
            "version": 1,
            "meta": {"strategy": "manual", "model": model},
            "ops": []
        }
        target_path.write_text(json.dumps(placeholder_edits, indent=2), encoding="utf-8")

    # validate using updatable closure
    current_edits = [edits]

    def validate_current() -> list[str]:
        if current_edits[0] is not None:
            return validate_edits(current_edits[0], resume_lines, risk)
        else:
            # return JSON parsing error as validation warning to trigger interactive handling
            return [json_error_warning] if json_error_warning else ["Edits not initialized"]

    def edit_edits_and_update(validation_warnings) -> dict | None:
        # load current edits from disk
        if settings.edits_path.exists():
            current_edits_json = settings.edits_path.read_text(encoding="utf-8")
        else:
            raise EditError("No existing edits file found for correction")

        # generate corrected edits via pipeline
        try:
            new_edits = generate_corrected_edits(
                current_edits_json,
                resume_lines,
                job_text,
                sections_json,
                model,
                validation_warnings,
            )
            # update current edits for validation
            current_edits[0] = new_edits
            return new_edits
        except JSONParsingError as e:
            # if regeneration also fails w/ JSON error, return None to continue validation loop
            current_edits[0] = None
            nonlocal json_error_warning
            json_error_warning = str(e)
            return None

    def reload_from_disk(data) -> None:
        current_edits[0] = data

    # perform validation
    result = handle_validation_error(
        settings,
        validate_fn=validate_current,
        policy=policy,
        edit_fn=edit_edits_and_update,
        reload_fn=reload_from_disk,
        ui=ui,
    )

    # handle regeneration result if present
    if isinstance(result, dict):
        edits = result
    elif edits is None:
        raise EditError("Failed to generate valid edits")

    return current_edits[0]


# * Convert dict-based edits to EditOperation objects for interactive display
def convert_dict_edits_to_operations(edits: dict, resume_lines: Lines) -> list[EditOperation]:
    operations = []
    ops = edits.get("ops", [])
    
    for op in ops:
        op_type = op["op"]
        
        # create EditOperation based on operation type
        if op_type == "replace_line":
            # get original content for display
            original_content = resume_lines.get(op["line"], "")
            operation = EditOperation(
                operation="replace_line",
                line_number=op["line"],
                content=op["text"],
                reasoning=op.get("reason", ""),
                confidence=op.get("confidence", 0.0),
                original_content=original_content
            )
        elif op_type == "replace_range":
            # get original content for range display
            original_lines = []
            for line_num in range(op["start"], op["end"] + 1):
                original_lines.append(resume_lines.get(line_num, ""))
            original_content = "\n".join(original_lines)
            operation = EditOperation(
                operation="replace_range",
                line_number=op["start"],
                start_line=op["start"],
                end_line=op["end"],
                content=op["text"],
                reasoning=op.get("reason", ""),
                confidence=op.get("confidence", 0.0),
                original_content=original_content
            )
        elif op_type == "insert_after":
            operation = EditOperation(
                operation="insert_after",
                line_number=op["line"],
                content=op["text"],
                reasoning=op.get("reason", ""),
                confidence=op.get("confidence", 0.0)
            )
        elif op_type == "delete_range":
            operation = EditOperation(
                operation="delete_range",
                line_number=op["start"],
                start_line=op["start"],
                end_line=op["end"],
                reasoning=op.get("reason", ""),
                confidence=op.get("confidence", 0.0)
            )
        else:
            continue
            
        # add before/after context for display (up to 2 lines each way)
        line_num = operation.line_number
        before_lines = []
        after_lines = []
        
        for i in range(max(1, line_num - 2), line_num):
            if i in resume_lines:
                before_lines.append(f"{i}: {resume_lines[i]}")
        
        end_line = operation.end_line if operation.end_line else line_num
        for i in range(end_line + 1, min(len(resume_lines) + 1, end_line + 3)):
            if i in resume_lines:
                after_lines.append(f"{i}: {resume_lines[i]}")
        
        operation.before_context = before_lines
        operation.after_context = after_lines
        operations.append(operation)
    
    return operations


# * Process MODIFY & PROMPT operations, requiring additional context
def process_special_operations(
    operations: list[EditOperation],
    resume_lines: Lines,
    job_text: str | None = None,
    sections_json: str | None = None,
    model: str | None = None,
) -> list[EditOperation]:
    from ..core.exceptions import AIError
    from ..loom_io.console import console
    
    for operation in operations:
        try:
            if operation.status == DiffOp.MODIFY:
                if operation.content:
                    process_modify_operation(operation)
                else:
                    console.print(f"[yellow]Warning: MODIFY operation at line {operation.line_number} has no content - skipping[/]")
                    
            elif operation.status == DiffOp.PROMPT:
                if operation.prompt_instruction is not None:
                    if job_text is None or model is None:
                        console.print(f"[red]Error: PROMPT operation at line {operation.line_number} requires job text and model - skipping[/]")
                        continue
                    process_prompt_operation(operation, resume_lines, job_text, sections_json, model)
                else:
                    console.print(f"[yellow]Warning: PROMPT operation at line {operation.line_number} has no prompt_instruction - skipping[/]")
                    
        except (EditError, AIError) as e:
            console.print(f"[red]Error processing {operation.status.value} operation at line {operation.line_number}: {e}[/]")
            # keep operation as-is but don't process it
            continue
    
    return operations


# * Convert approved EditOperation objects back to dict format for application
def convert_operations_to_dict_edits(operations: list[EditOperation], original_edits: dict) -> dict:
    approved_ops = []
    
    for op in operations:
        if op.status != DiffOp.APPROVE:
            continue
            
        # convert back to dict format
        if op.operation == "replace_line":
            dict_op = {
                "op": "replace_line",
                "line": op.line_number,
                "text": op.content
            }
        elif op.operation == "replace_range":
            dict_op = {
                "op": "replace_range",
                "start": op.start_line,
                "end": op.end_line,
                "text": op.content
            }
        elif op.operation == "insert_after":
            dict_op = {
                "op": "insert_after",
                "line": op.line_number,
                "text": op.content
            }
        elif op.operation == "delete_range":
            dict_op = {
                "op": "delete_range",
                "start": op.start_line,
                "end": op.end_line
            }
        else:
            continue  # skip unknown operations
            
        # preserve original metadata if available
        if hasattr(op, 'reasoning') and op.reasoning:
            dict_op["reason"] = op.reasoning
        if hasattr(op, 'confidence') and op.confidence:
            dict_op["confidence"] = op.confidence
            
        approved_ops.append(dict_op)
    
    # return new edits dict w/ only approved operations
    return {
        "version": original_edits.get("version", 1),
        "meta": original_edits.get("meta", {}),
        "ops": approved_ops
    }


# * Convert ALL EditOperation objects back to dict format for persistence
def convert_all_operations_to_dict_edits(operations: list[EditOperation], original_edits: dict) -> dict:
    all_ops = []
    
    for op in operations:
        # convert back to dict format
        if op.operation == "replace_line":
            dict_op = {
                "op": "replace_line",
                "line": op.line_number,
                "text": op.content
            }
        elif op.operation == "replace_range":
            dict_op = {
                "op": "replace_range",
                "start": op.start_line,
                "end": op.end_line,
                "text": op.content
            }
        elif op.operation == "insert_after":
            dict_op = {
                "op": "insert_after",
                "line": op.line_number,
                "text": op.content
            }
        elif op.operation == "delete_range":
            dict_op = {
                "op": "delete_range",
                "start": op.start_line,
                "end": op.end_line
            }
        else:
            continue  # skip unknown operations
            
        # preserve original metadata if available
        if hasattr(op, 'reasoning') and op.reasoning:
            dict_op["reason"] = op.reasoning
        if hasattr(op, 'confidence') and op.confidence:
            dict_op["confidence"] = op.confidence
        
        # track user decision status
        dict_op["_status"] = op.status.value
            
        all_ops.append(dict_op)
    
    # return new edits dict w/ all operations & their statuses
    return {
        "version": original_edits.get("version", 1),
        "meta": original_edits.get("meta", {}),
        "ops": all_ops
    }


# * Validate & apply edits to resume lines, returning new lines
def apply_edits_core(
    settings: LoomSettings,
    resume_lines: Lines,
    edits: dict,
    risk: RiskLevel,
    policy: ValidationPolicy,
    ui,
    interactive: bool = False,
    job_text: str | None = None,
    sections_json: str | None = None,
    model: str | None = None,
    persist_special_ops: bool = False,
    edits_json_path: Path | None = None,
) -> Lines:
    # use mutable container for reload support
    current = [edits]

    def validate_current() -> list[str]:
        return validate_edits(current[0], resume_lines, risk)

    def reload_from_disk(data) -> None:
        current[0] = data

    # validate before applying edits
    handle_validation_error(
        settings,
        validate_fn=validate_current,
        policy=policy,
        reload_fn=reload_from_disk,
        ui=ui,
    )

    # implement interactive diff review if interactive=True
    if interactive:
        # convert dict edits to EditOperation objects for display
        operations = convert_dict_edits_to_operations(current[0], resume_lines)
        
        if not operations:
            # no operations to review - proceed w/ empty edits
            current[0] = {"version": current[0].get("version", 1), "meta": current[0].get("meta", {}), "ops": []}
        else:
            # process MODIFY & PROMPT operations before interactive review
            special_ops_processed = False
            if job_text is not None or any(op.status in (DiffOp.MODIFY, DiffOp.PROMPT) for op in operations):
                operations = process_special_operations(operations, resume_lines, job_text, sections_json, model)
                special_ops_processed = True
            
            # run interactive diff display for user review
            filename = "resume.docx"  # default filename for display
            reviewed_operations, operations_modified_during_review = main_display_loop(
                operations, 
                filename, 
                resume_lines=resume_lines,
                job_text=job_text,
                sections_json=sections_json,
                model=model
            )
            
            # convert approved operations back to dict format
            current[0] = convert_operations_to_dict_edits(reviewed_operations, current[0])
            
            # persist special operations back to edits.json if requested
            if persist_special_ops and (special_ops_processed or operations_modified_during_review) and edits_json_path is not None:
                
                # create updated edits dict w/ all operations (including their statuses)
                complete_edits = convert_all_operations_to_dict_edits(reviewed_operations, current[0])
                
                # write updated edits back to file
                ensure_parent(edits_json_path)
                edits_json_path.write_text(json.dumps(complete_edits, indent=2), encoding="utf-8")
                ui.print(f"[green]Updated edits saved to {edits_json_path}[/]")
    
    # execute edit application w/ approved operations only
    return apply_edits(resume_lines, current[0])
