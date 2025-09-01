# src/cli/commands/prompt.py
# Prompt command for processing PROMPT operations in edits.json w/ AI generation

from __future__ import annotations

import json
from pathlib import Path
import typer

from ...core.constants import RiskLevel, ValidationPolicy, DiffOp
from ...core.exceptions import handle_loom_error, EditError, AIError
from ...core.pipeline import process_prompt_operation

from ..app import app
from ..helpers import validate_required_args
from ...ui.core.progress import setup_ui_with_progress, load_edits_json, load_sections
from ...ui.display.reporting import persist_edits_json, report_result
from ..logic import ArgResolver, convert_dict_edits_to_operations, convert_operations_to_dict_edits
from ..params import EditsJsonOpt, ResumeArg, JobArg, ModelOpt, SectionsPathOpt, OutputEditsOpt
from ...loom_io import read_resume
from ...config.settings import get_settings


# * Process PROMPT operations in edits.json w/ AI-generated content
@app.command(help="Process PROMPT operations in edits.json with AI-generated content")
@handle_loom_error
def prompt(
    ctx: typer.Context,
    edits_json: Path | None = EditsJsonOpt(),
    resume: Path | None = ResumeArg(),
    job: Path | None = JobArg(),
    model: str | None = ModelOpt(),
    sections_path: Path | None = SectionsPathOpt(),
    output_edits: Path | None = OutputEditsOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & show custom help
    if help:
        from .help import show_command_help
        show_command_help("prompt")
        ctx.exit()
    
    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    # resolve arguments w/ settings defaults
    common_resolved = resolver.resolve_common(
        edits_json=edits_json,
        resume=resume,
        job=job,
        model=model,
        sections_path=sections_path,
    )
    edits_json, resume, job, model, sections_path = (
        common_resolved["edits_json"],
        common_resolved["resume"],
        common_resolved["job"],
        common_resolved["model"],
        common_resolved["sections_path"],
    )
    
    # default output to input path if not specified
    if output_edits is None:
        output_edits = edits_json

    # validate required arguments
    validate_required_args(
        edits_json=(edits_json, "Edits JSON path"),
        resume=(resume, "Resume path"),
        job=(job, "Job description path"),
        model=(model, "Model (provide --model or set in config)"),
    )

    # type assertions after validation
    assert edits_json is not None
    assert resume is not None
    assert job is not None
    assert model is not None
    assert output_edits is not None

    with setup_ui_with_progress("Processing PROMPT operations...", total=7) as (
        ui,
        progress,
        task,
    ):
        # read resume for context
        progress.update(task, description="Reading resume document...")
        resume_lines = read_resume(resume)
        progress.advance(task)

        # read job description
        progress.update(task, description="Reading job description...")
        job_text = Path(job).read_text(encoding="utf-8")
        progress.advance(task)

        # load optional sections
        sections_json_str = load_sections(sections_path, progress, task)

        # read edits
        edits_obj = load_edits_json(edits_json, progress, task)

        # convert to EditOperation objects
        progress.update(task, description="Converting edits to operations...")
        operations = convert_dict_edits_to_operations(edits_obj, resume_lines)
        progress.advance(task)

        # process PROMPT operations
        progress.update(task, description="Processing PROMPT operations with AI...")
        processed_count = 0
        error_count = 0
        
        for operation in operations:
            if operation.status == DiffOp.PROMPT:
                if operation.prompt_instruction is None:
                    ui.print(f"[yellow]Warning: PROMPT operation at line {operation.line_number} has no prompt_instruction - skipping[/]")
                    continue
                
                try:
                    process_prompt_operation(operation, resume_lines, job_text, sections_json_str, model)
                    processed_count += 1
                    ui.print(f"[green]Processed PROMPT operation at line {operation.line_number}[/]")
                except (EditError, AIError) as e:
                    ui.print(f"[red]Error processing PROMPT operation at line {operation.line_number}: {e}[/]")
                    error_count += 1
                    continue
        
        if processed_count == 0:
            ui.print("[yellow]No PROMPT operations found or processed[/]")
        else:
            ui.print(f"[green]Processed {processed_count} PROMPT operations[/]")
            if error_count > 0:
                ui.print(f"[red]{error_count} operations failed[/]")
        
        progress.advance(task)

        # convert back to dict format
        progress.update(task, description="Converting operations back to edits...")
        processed_edits = convert_operations_to_dict_edits(operations, edits_obj)
        progress.advance(task)

        # write processed edits
        persist_edits_json(processed_edits, output_edits, progress, task)

    report_result("prompt", edits_path=output_edits, processed_count=processed_count, error_count=error_count)