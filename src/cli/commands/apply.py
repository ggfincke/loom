# src/cli/commands/apply.py
# Apply command for executing edits.json operations on resume documents

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import handle_help_flag, is_test_environment
from ..logic import ArgResolver
from ..runner import TailoringMode, TailoringRunner, build_tailoring_context
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
from ...config.settings import get_settings


# * Apply edits from JSON to resume document & generate tailored output
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
    help: bool = typer.Option(False, "--help", "-h", help="Show help message & exit."),
) -> None:
    handle_help_flag(ctx, help, "apply")

    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    # determine interactive mode: use interactive setting unless in test environment
    interactive_mode = settings.interactive and not is_test_environment()

    tailoring_ctx = build_tailoring_context(
        settings,
        resolver,
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

    runner = TailoringRunner(TailoringMode.APPLY, tailoring_ctx)
    runner.run()
