# src/cli/commands/generate.py
# Generate command for creating edits.json w/ AI-powered resume tailoring

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import handle_help_flag, run_tailoring_command
from ..runner import TailoringMode
from ..params import (
    ModelOpt,
    EditsJsonOpt,
    SectionsPathOpt,
    ResumeArg,
    JobArg,
    RiskOpt,
    OnErrorOpt,
)
from ...ui.help.help_data import command_help


# * Generate edits.json for resume tailoring using AI model & job requirements
@command_help(
    name="generate",
    description="Generate edits.json with AI-powered resume tailoring",
    long_description=(
        "Analyze job description and produce structured edits.json file "
        "containing modifications to optimize your resume for specific job "
        "requirements. Review edits before applying with 'loom apply'."
    ),
    examples=[
        "loom generate job.txt resume.docx",
        "loom generate job.txt resume.docx --model gpt-4o",
        "loom generate job.txt resume.docx --edits-json my_edits.json",
        "loom generate job.txt resume.docx --risk high",
    ],
    see_also=["apply", "tailor", "sectionize", "plan"],
)
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

    run_tailoring_command(
        ctx,
        TailoringMode.GENERATE,
        resume=resume,
        job=job,
        model=model,
        sections_path=sections_path,
        edits_json=edits_json,
        risk=risk,
        on_error=on_error,
    )
