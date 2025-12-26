# src/cli/commands/generate.py
# Generate command for creating edits.json w/ AI-powered resume tailoring

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import handle_help_flag
from ..logic import ArgResolver
from ..runner import TailoringMode, TailoringRunner, build_tailoring_context
from ..params import (
    ModelOpt,
    EditsJsonOpt,
    SectionsPathOpt,
    ResumeArg,
    JobArg,
    RiskOpt,
    OnErrorOpt,
)
from ...config.settings import get_settings


# * Generate edits.json for resume tailoring using AI model & job requirements
@app.command(
    help="Generate edits.json with AI-powered resume tailoring for job requirements"
)
@handle_loom_error
def generate(
    ctx: typer.Context,
    model: Optional[str] = ModelOpt(),
    edits_json: Optional[Path] = EditsJsonOpt(),
    sections_path: Optional[Path] = SectionsPathOpt(),
    resume: Optional[Path] = ResumeArg(),
    job: Optional[Path] = JobArg(),
    risk: Optional[RiskLevel] = RiskOpt(),
    on_error: Optional[ValidationPolicy] = OnErrorOpt(),
    help: bool = typer.Option(
        False, "--help", "-h", help="Show help message and exit."
    ),
) -> None:
    handle_help_flag(ctx, help, "generate")

    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    tailoring_ctx = build_tailoring_context(
        settings,
        resolver,
        resume=resume,
        job=job,
        model=model,
        sections_path=sections_path,
        edits_json=edits_json,
        risk=risk,
        on_error=on_error,
    )

    runner = TailoringRunner(TailoringMode.GENERATE, tailoring_ctx)
    runner.run()
