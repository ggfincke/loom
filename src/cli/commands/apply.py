# src/cli/commands/apply.py
# Apply command for executing edits.json operations on resume documents

from __future__ import annotations

from pathlib import Path
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import validate_required_args, is_test_environment
from ...ui.core.progress import setup_ui_with_progress, load_edits_json
from ...ui.display.reporting import report_result, write_output_with_diff
from ..logic import ArgResolver, apply_edits_core
from ..params import (
    ResumeArg,
    EditsJsonOpt,
    OutputResumeOpt,
    RiskOpt,
    OnErrorOpt,
    PreserveFormattingOpt,
    PreserveModeOpt,
    JobArg,
    ModelOpt,
    SectionsPathOpt,
)
from ...loom_io import read_resume
from ...config.settings import get_settings


# * Apply edits from JSON to resume document & generate tailored output
@app.command(help="Apply edits from JSON to resume document & generate tailored output")
@handle_loom_error
def apply(
    ctx: typer.Context,
    resume: Path | None = ResumeArg(),
    edits_json: Path | None = EditsJsonOpt(),
    output_resume: Path | None = OutputResumeOpt(),
    risk: RiskLevel | None = RiskOpt(),
    on_error: ValidationPolicy | None = OnErrorOpt(),
    preserve_formatting: bool = PreserveFormattingOpt(),
    preserve_mode: str = PreserveModeOpt(),
    job: Path | None = JobArg(),
    model: str | None = ModelOpt(),
    sections_path: Path | None = SectionsPathOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & show custom help
    if help:
        from .help import show_command_help
        show_command_help("apply")
        ctx.exit()
    settings = get_settings(ctx)
    resolver = ArgResolver(settings)
    
    # determine interactive mode: use interactive setting unless in test environment
    interactive_mode = settings.interactive and not is_test_environment()

    # resolve arguments w/ settings defaults
    common_resolved = resolver.resolve_common(
        resume=resume, 
        edits_json=edits_json,
        job=job,
        model=model,
        sections_path=sections_path
    )
    path_resolved = resolver.resolve_paths(output_resume=output_resume)
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)

    resume, edits_json, job, model, sections_path = (
        common_resolved["resume"],
        common_resolved["edits_json"],
        common_resolved["job"],
        common_resolved["model"],
        common_resolved["sections_path"],
    )
    output_resume = path_resolved["output_resume"]
    risk, on_error = option_resolved["risk"], option_resolved["on_error"]

    # validate required arguments
    validate_required_args(
        resume=(resume, "Resume path"),
        edits_json=(edits_json, "Edits path"),
        output_resume=(output_resume, "Output path"),
    )

    # type assertions after validation
    assert resume is not None
    assert edits_json is not None
    assert output_resume is not None

    # calculate total steps (base 5 + optional job/sections)
    total_steps = 5
    if job is not None:
        total_steps += 1
    if sections_path is not None:
        total_steps += 1
        
    with setup_ui_with_progress("Applying edits...", total=total_steps) as (
        ui,
        progress,
        task,
    ):
        # read resume
        progress.update(task, description="Reading resume document...")
        lines = read_resume(resume)
        progress.advance(task)
        
        # read job description if available (for prompt support)
        job_text = None
        if job is not None:
            progress.update(task, description="Reading job description...")
            job_text = Path(job).read_text(encoding="utf-8")
            progress.advance(task)
            
        # load optional sections for prompt support
        from ...ui.core.progress import load_sections
        sections_json_str = load_sections(sections_path, progress, task) if sections_path else None

        # read edits
        edits_obj = load_edits_json(edits_json, progress, task)

        # apply edits using core helper
        progress.update(task, description="Applying edits...")
        new_lines = apply_edits_core(
            settings, lines, edits_obj, risk, on_error, ui, interactive_mode,
            job_text=job_text, sections_json=sections_json_str, model=model,
            persist_special_ops=interactive_mode, edits_json_path=edits_json
        )
        progress.advance(task)

        # write output w/ diff generation
        write_output_with_diff(
            settings,
            resume,
            lines,
            new_lines,
            output_resume,
            preserve_formatting,
            preserve_mode,
            progress,
            task,
        )

    report_result(
        "apply",
        settings=settings,
        output_path=output_resume,
        preserve_formatting=preserve_formatting,
        preserve_mode=preserve_mode,
    )
