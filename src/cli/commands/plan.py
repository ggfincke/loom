# src/cli/commands/plan.py
# Plan command for generating edits w/ step-by-step planning workflow

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy

from ..app import app
from ..decorators import handle_loom_error
from ..helpers import handle_help_flag, run_tailoring_command
from ..runner import TailoringMode
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
    handle_help_flag(ctx, help, "plan")

    # Unused but planned
    _ = plan

    run_tailoring_command(
        ctx,
        TailoringMode.PLAN,
        resume=resume,
        job=job,
        model=model,
        sections_path=sections_path,
        edits_json=edits_json,
        risk=risk,
        on_error=on_error,
    )
