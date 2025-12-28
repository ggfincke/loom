# src/cli/commands/apply.py
# Apply command for executing edits.json operations on resume documents

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy

from ..app import app
from ..decorators import handle_loom_error, run_with_watch
from ..helpers import handle_help_flag, is_test_environment, run_tailoring_command
from ..runner import TailoringMode
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
    WatchOpt,
)
from ...config.settings import get_settings
from ...ui.help.help_data import command_help


# * Apply edits from JSON to resume document & generate tailored output
@command_help(
    name="apply",
    description="Apply edits from JSON to resume document",
    long_description=(
        "Apply pre-generated edits from edits.json to your resume, "
        "creating a tailored output document. Supports interactive "
        "diff review, formatting preservation, and validation policies."
    ),
    examples=[
        "loom apply resume.docx --edits-json edits.json",
        "loom apply resume.docx --output-resume tailored.docx",
        "loom apply resume.docx --no-preserve-formatting",
        "loom apply resume.docx --risk conservative",
        "loom apply resume.docx --edits-json edits.json --watch",
    ],
    see_also=["generate", "tailor"],
)
@app.command(help="Apply edits from JSON to resume document & generate tailored output")
@handle_loom_error
def apply(
    ctx: typer.Context,
    resume: Optional[Path] = ResumeArg(),
    edits_json: Optional[Path] = EditsJsonOpt(),
    output_resume: Optional[Path] = OutputResumeOpt(),
    risk: Optional[RiskLevel] = RiskOpt(),
    on_error: Optional[ValidationPolicy] = OnErrorOpt(),
    preserve_formatting: bool = PreserveFormattingOpt(),
    preserve_mode: str = PreserveModeOpt(),
    job: Optional[Path] = JobArg(),
    model: Optional[str] = ModelOpt(),
    sections_path: Optional[Path] = SectionsPathOpt(),
    watch: bool = WatchOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message & exit."),
) -> None:
    handle_help_flag(ctx, help, "apply")

    # Determine interactive mode: use interactive setting unless in test env
    # Watch mode implies non-interactive (auto mode)
    settings = get_settings(ctx)
    interactive_mode = settings.interactive and not is_test_environment() and not watch

    # Watch mode: wrap execution in file watcher
    if watch:
        run_with_watch(
            paths=[resume, edits_json, sections_path],
            run_func=lambda: run_tailoring_command(
                ctx,
                TailoringMode.APPLY,
                resume=resume,
                job=job,
                model=model,
                sections_path=sections_path,
                edits_json=edits_json,
                output_resume=output_resume,
                risk=risk,
                on_error=on_error,
                preserve_formatting=preserve_formatting,
                preserve_mode=preserve_mode,
                interactive=False,
            ),
            debounce=settings.watch_debounce,
        )
        return

    run_tailoring_command(
        ctx,
        TailoringMode.APPLY,
        resume=resume,
        job=job,
        model=model,
        sections_path=sections_path,
        edits_json=edits_json,
        output_resume=output_resume,
        risk=risk,
        on_error=on_error,
        preserve_formatting=preserve_formatting,
        preserve_mode=preserve_mode,
        interactive=interactive_mode,
    )
