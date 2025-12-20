# src/cli/commands/plan.py
# Plan command for generating edits w/ step-by-step planning workflow

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..logic import ArgResolver
from ..runner import TailoringMode, TailoringRunner, build_tailoring_context
from ..params import (
    ResumeArg,
    JobArg,
    EditsJsonOpt,
    PlanOpt,
    RiskOpt,
    OnErrorOpt,
    ModelOpt,
    SectionsPathOpt,
)
from ...ui.help.help_data import command_help
from ...config.settings import get_settings


# * Generate edits w/ step-by-step planning & validation workflow
@command_help(
    name="plan",
    description="Generate edits with step-by-step planning workflow (experimental)",
    long_description=(
        "Experimental command that uses a multi-step planning approach for "
        "resume tailoring. Provides more detailed reasoning and step-by-step "
        "edit generation for complex tailoring scenarios. Accepts the same "
        "options as 'tailor' for risk and validation policies."
    ),
    examples=[
        "loom plan job.txt resume.docx",
        "loom plan job.txt resume.docx --sections-path sections.json",
        "loom plan job.txt resume.docx --edits-json planned_edits.json",
    ],
    see_also=["tailor"],
)
@app.command(help="Generate edits with step-by-step planning workflow (experimental)")
@handle_loom_error
def plan(
    ctx: typer.Context,
    resume: Optional[Path] = ResumeArg(),
    job: Optional[Path] = JobArg(),
    edits_json: Optional[Path] = EditsJsonOpt(),
    plan: Optional[int] = PlanOpt(),
    risk: Optional[RiskLevel] = RiskOpt(),
    on_error: Optional[ValidationPolicy] = OnErrorOpt(),
    model: Optional[str] = ModelOpt(),
    sections_path: Optional[Path] = SectionsPathOpt(),
    help: bool = typer.Option(
        False, "--help", "-h", help="Show help message and exit."
    ),
) -> None:
    # detect help flag & show custom help
    if help:
        from .help import show_command_help

        show_command_help("plan")
        ctx.exit()

    # unused but planned
    _ = plan

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

    runner = TailoringRunner(TailoringMode.PLAN, tailoring_ctx)
    runner.run()
