# src/cli/commands/modify.py
# Modify command for processing MODIFY operations in edits.json

from __future__ import annotations

import json
from pathlib import Path
import typer

from ...core.constants import RiskLevel, ValidationPolicy, DiffOp
from ...core.exceptions import handle_loom_error, EditError
from ...core.pipeline import process_modify_operation

from ..app import app
from ..helpers import validate_required_args
from ...ui.core.progress import setup_ui_with_progress, load_edits_json
from ...ui.display.reporting import persist_edits_json, report_result
from ..logic import ArgResolver, convert_dict_edits_to_operations, convert_operations_to_dict_edits
from ..params import EditsJsonOpt, ResumeArg, OutputEditsOpt
from ...loom_io import read_resume
from ...config.settings import get_settings


# * Process MODIFY operations in edits.json with user-modified content
@app.command(help="Process MODIFY operations in edits.json with user-modified content")
@handle_loom_error
def modify(
    ctx: typer.Context,
    edits_json: Path | None = EditsJsonOpt(),
    resume: Path | None = ResumeArg(),
    output_edits: Path | None = OutputEditsOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & show custom help
    if help:
        from .help import show_command_help
        show_command_help("modify")
        ctx.exit()
    
    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    # resolve arguments w/ settings defaults
    common_resolved = resolver.resolve_common(edits_json=edits_json, resume=resume)
    edits_json, resume = common_resolved["edits_json"], common_resolved["resume"]
    
    # default output to input path if not specified
    if output_edits is None:
        output_edits = edits_json

    # validate required arguments
    validate_required_args(
        edits_json=(edits_json, "Edits JSON path"),
        resume=(resume, "Resume path"),
    )

    # type assertions after validation
    assert edits_json is not None
    assert resume is not None
    assert output_edits is not None

    with setup_ui_with_progress("Processing MODIFY operations...", total=5) as (
        ui,
        progress,
        task,
    ):
        # read resume for context
        progress.update(task, description="Reading resume document...")
        resume_lines = read_resume(resume)
        progress.advance(task)

        # read edits
        edits_obj = load_edits_json(edits_json, progress, task)

        # convert to EditOperation objects
        progress.update(task, description="Converting edits to operations...")
        operations = convert_dict_edits_to_operations(edits_obj, resume_lines)
        progress.advance(task)

        # process MODIFY operations
        progress.update(task, description="Processing MODIFY operations...")
        processed_count = 0
        for operation in operations:
            if operation.status == DiffOp.MODIFY:
                if operation.modified_content is None:
                    ui.print(f"[yellow]Warning: MODIFY operation at line {operation.line_number} has no modified_content - skipping[/]")
                    continue
                
                try:
                    process_modify_operation(operation)
                    processed_count += 1
                except EditError as e:
                    ui.print(f"[red]Error processing MODIFY operation at line {operation.line_number}: {e}[/]")
                    continue
        
        if processed_count == 0:
            ui.print("[yellow]No MODIFY operations found or processed[/]")
        else:
            ui.print(f"[green]Processed {processed_count} MODIFY operations[/]")
        
        progress.advance(task)

        # convert back to dict format
        progress.update(task, description="Converting operations back to edits...")
        processed_edits = convert_operations_to_dict_edits(operations, edits_obj)
        progress.advance(task)

        # write processed edits
        persist_edits_json(processed_edits, output_edits, progress, task)

    report_result("modify", edits_path=output_edits, processed_count=processed_count)