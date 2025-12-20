# src/cli/commands/tailor.py
# Tailor command for complete end-to-end resume tailoring workflow w/ generation & application

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import is_test_environment
from ..logic import ArgResolver
from ..runner import TailoringMode, TailoringRunner, build_tailoring_context
from ..params import (
    JobArg,
    ResumeArg,
    ModelOpt,
    SectionsPathOpt,
    EditsJsonOpt,
    OutputResumeOpt,
    RiskOpt,
    OnErrorOpt,
    PreserveFormattingOpt,
    PreserveModeOpt,
    AutoOpt,
)
from ...ui.help.help_data import command_help
from ...config.settings import get_settings


# * Complete end-to-end resume tailoring: generate edits & apply to create tailored resume
@command_help(
    name="tailor",
    description="Complete end-to-end resume tailoring: generate edits & apply in one step",
    long_description=(
        "run generation & apply in one pass: analyze job description, "
        "produce edits & write tailored resume. Accepts same safety "
        "and formatting controls as 'generate'/'apply'. Use --edits-only to stop "
        "after generating edits, or --apply to apply existing edits."
    ),
    examples=[
        "loom tailor job.txt resume.docx",
        "loom tailor job.txt resume.docx --output-resume custom_name.docx",
        "loom tailor job.txt resume.docx --sections-path sections.json",
        "loom tailor job.txt resume.docx --edits-only",
        "loom tailor resume.docx --apply --output-resume tailored.docx",
        "loom tailor job.txt resume.docx --no-preserve-formatting",
    ],
    see_also=["sectionize", "plan"],
)
@app.command(
    help="Complete end-to-end resume tailoring: generate edits & apply in one step"
)
@handle_loom_error
def tailor(
    ctx: typer.Context,
    job: Optional[Path] = JobArg(),
    resume: Optional[Path] = ResumeArg(),
    model: Optional[str] = ModelOpt(),
    sections_path: Optional[Path] = SectionsPathOpt(),
    edits_json: Optional[Path] = EditsJsonOpt(),
    output_resume: Optional[Path] = OutputResumeOpt(),
    risk: Optional[RiskLevel] = RiskOpt(),
    on_error: Optional[ValidationPolicy] = OnErrorOpt(),
    preserve_formatting: bool = PreserveFormattingOpt(),
    preserve_mode: str = PreserveModeOpt(),
    edits_only: bool = typer.Option(
        False, "--edits-only", help="Generate edits JSON only (don't apply)"
    ),
    apply: bool = typer.Option(
        False, "--apply", help="Apply existing edits JSON to resume"
    ),
    auto: bool = AutoOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message & exit."),
) -> None:
    # detect help flag & display custom help
    if help:
        from .help import show_command_help

        show_command_help("tailor")
        ctx.exit()

    # validate mutually exclusive flags
    if edits_only and apply:
        from ...loom_io.console import console

        console.print("[red]Error: --edits-only & --apply are mutually exclusive[/]")
        ctx.exit(1)

    # determine mode
    if apply:
        mode = TailoringMode.APPLY
    elif edits_only:
        mode = TailoringMode.GENERATE
    else:
        mode = TailoringMode.TAILOR

    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    # determine interactive mode: use interactive setting unless --auto flag specified or in test env
    interactive_mode = settings.interactive and not auto and not is_test_environment()

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

    runner = TailoringRunner(mode, tailoring_ctx)
    runner.run()
