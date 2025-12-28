# src/cli/commands/tailor.py
# Tailor command for complete end-to-end resume tailoring workflow w/ generation & application

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
    UserPromptOpt,
    NoCacheOpt,
    WatchOpt,
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
        'loom tailor job.txt resume.docx --prompt "Emphasize leadership experience"',
        "loom tailor job.txt resume.docx --watch",
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
    user_prompt: Optional[str] = UserPromptOpt(),
    no_cache: bool = NoCacheOpt(),
    watch: bool = WatchOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message & exit."),
) -> None:
    handle_help_flag(ctx, help, "tailor")

    # Disable cache if --no-cache flag is set
    if no_cache:
        from ...ai.cache import disable_cache_for_invocation

        disable_cache_for_invocation()

    # Validate mutually exclusive flags
    if edits_only and apply:
        from ...loom_io.console import console

        console.print("[red]Error: --edits-only & --apply are mutually exclusive[/]")
        ctx.exit(1)

    # Determine mode
    if apply:
        mode = TailoringMode.APPLY
    elif edits_only:
        mode = TailoringMode.GENERATE
    else:
        mode = TailoringMode.TAILOR

    # Determine interactive mode: use interactive setting unless --auto or in test env
    # Watch mode implies auto (no interactive prompts on each re-run)
    settings = get_settings(ctx)
    if watch:
        auto = True
    interactive_mode = settings.interactive and not auto and not is_test_environment()

    # Watch mode: wrap execution in file watcher
    if watch:
        run_with_watch(
            paths=[resume, job, sections_path],
            run_func=lambda: run_tailoring_command(
                ctx,
                mode,
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
                user_prompt=user_prompt,
            ),
            debounce=settings.watch_debounce,
        )
        return

    run_tailoring_command(
        ctx,
        mode,
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
        user_prompt=user_prompt,
    )
