# src/cli/commands/tailor.py
# Tailor command for complete end-to-end resume tailoring workflow w/ generation & application

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import validate_required_args, is_test_environment
from ...ui.core.progress import (
    setup_ui_with_progress,
    load_resume_and_job,
    load_sections,
)
from ...ui.display.reporting import (
    persist_edits_json,
    report_result,
    write_output_with_diff,
)
from ..logic import (
    ArgResolver,
    generate_edits_core,
    apply_edits_core,
    build_latex_context,
)
from ...loom_io import read_resume, TemplateDescriptor
from ...loom_io.types import Lines
from ...ui.help.help_data import command_help
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
from ...config.settings import get_settings


def _prepare_resume_context(
    resume_path: Path,
    job_path: Path | None,
    is_latex: bool,
    progress,
    task,
) -> tuple[
    Lines,
    str | None,
    TemplateDescriptor | None,
    str | None,
    list[str],
]:
    if job_path is not None:
        lines, job_text = load_resume_and_job(resume_path, job_path, progress, task)
    else:
        progress.update(task, description="Reading resume document...")
        lines = read_resume(resume_path)
        progress.advance(task)
        job_text = None

    descriptor = None
    auto_sections_json = None
    template_notes: list[str] = []
    if is_latex:
        progress.update(task, description="Analyzing LaTeX structure...")
        descriptor, auto_sections_json, template_notes = build_latex_context(
            resume_path, lines
        )
        progress.advance(task)

    return lines, job_text, descriptor, auto_sections_json, template_notes


def _display_latex_info(
    ui, descriptor: TemplateDescriptor | None, template_notes: list[str]
) -> None:
    if descriptor:
        ui.print(f"[green]Detected LaTeX template:[/] {descriptor.id}")
    if template_notes:
        ui.print("[yellow]Template notes:[/]")
        for note in template_notes:
            ui.print(f" - {note}")


def _resolve_sections_context(
    sections_path: Path | None,
    is_latex: bool,
    auto_sections_json: str | None,
    progress,
    task,
) -> str | None:
    if sections_path:
        return load_sections(sections_path, progress, task)
    if is_latex:
        return auto_sections_json
    return None


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

    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    # determine interactive mode: use interactive setting unless --auto flag specified or in test env
    interactive_mode = settings.interactive and not auto and not is_test_environment()

    # resolve args using settings defaults
    common_resolved = resolver.resolve_common(
        job=job,
        resume=resume,
        model=model,
        sections_path=sections_path,
        edits_json=edits_json,
    )
    path_resolved = resolver.resolve_paths(
        resume_path=common_resolved["resume"], output_resume=output_resume
    )
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)

    job, resume, model, sections_path, edits_json = (
        common_resolved["job"],
        common_resolved["resume"],
        common_resolved["model"],
        common_resolved["sections_path"],
        common_resolved["edits_json"],
    )
    output_resume = path_resolved["output_resume"]
    risk_enum: RiskLevel = option_resolved["risk"]
    on_error_policy: ValidationPolicy = option_resolved["on_error"]

    # validate required arguments by mode
    if apply:
        # apply mode: require resume, edits_json, output_resume
        validate_required_args(
            resume=(resume, "Resume path"),
            output_resume=(
                output_resume,
                "Output resume path (provide argument or set output_dir in config)",
            ),
        )
    elif edits_only:
        # edits-only mode: require job, resume, model
        validate_required_args(
            job=(job, "Job description path"),
            resume=(resume, "Resume path"),
            model=(model, "Model (provide --model or set in config)"),
        )
    else:
        # full tailor mode: require all parameters
        validate_required_args(
            job=(job, "Job description path"),
            resume=(resume, "Resume path"),
            model=(model, "Model (provide --model or set in config)"),
            output_resume=(
                output_resume,
                "Output resume path (provide argument or set output_dir in config)",
            ),
        )

    # assert types after validation
    assert resume is not None
    assert edits_json is not None

    if not apply:
        # job & model required for generation
        assert job is not None
        assert model is not None

    if not edits_only:
        # output_resume required for application
        assert output_resume is not None

    is_latex = resume.suffix.lower() == ".tex"

    if apply:
        # apply mode: read edits & apply to resume
        assert output_resume is not None

        from ...ui.core.progress import load_edits_json

        apply_total = 5 + (1 if is_latex else 0) + (1 if sections_path else 0)
        with setup_ui_with_progress("Applying edits...", total=apply_total) as (
            ui,
            progress,
            task,
        ):
            lines, _, descriptor, auto_sections_json, template_notes = (
                _prepare_resume_context(resume, None, is_latex, progress, task)
            )
            _display_latex_info(ui, descriptor, template_notes)
            sections_json_str = _resolve_sections_context(
                sections_path, is_latex, auto_sections_json, progress, task
            )

            # read edits
            edits_obj = load_edits_json(edits_json, progress, task)

            # apply edits using core helper
            progress.update(task, description="Applying edits...")
            new_lines = apply_edits_core(
                settings,
                lines,
                edits_obj,
                risk_enum,
                on_error_policy,
                ui,
                interactive_mode,
                persist_special_ops=interactive_mode,
                edits_json_path=edits_json,
                resume_path=resume,
                sections_json=sections_json_str,
                descriptor=descriptor,
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

    elif edits_only:
        # edits-only mode: generate edits only
        assert job is not None
        assert model is not None

        edits_total = 4 + (1 if is_latex else 0) + (1 if sections_path else 0)
        with setup_ui_with_progress("Generating edits...", total=edits_total) as (
            ui,
            progress,
            task,
        ):
            lines, job_text, descriptor, auto_sections_json, template_notes = (
                _prepare_resume_context(resume, job, is_latex, progress, task)
            )
            _display_latex_info(ui, descriptor, template_notes)
            sections_json_str = _resolve_sections_context(
                sections_path, is_latex, auto_sections_json, progress, task
            )

            # generate edits using core helper
            progress.update(task, description="Generating edits with AI...")
            edits = generate_edits_core(
                settings,
                lines,
                job_text,
                sections_json_str,
                model,
                risk_enum,
                on_error_policy,
                ui,
                persist_path=edits_json,
            )
            progress.advance(task)

            # write edits
            if edits is None:
                from ...core.exceptions import EditError

                raise EditError("Failed to generate valid edits")
            persist_edits_json(edits, edits_json, progress, task)

    else:
        # full tailor mode: generate & apply edits
        assert job is not None
        assert model is not None
        assert output_resume is not None

        tailor_total = 7 + (1 if is_latex else 0) + (1 if sections_path else 0)
        with setup_ui_with_progress("Tailoring resume...", total=tailor_total) as (
            ui,
            progress,
            task,
        ):
            lines, job_text, descriptor, auto_sections_json, template_notes = (
                _prepare_resume_context(resume, job, is_latex, progress, task)
            )
            _display_latex_info(ui, descriptor, template_notes)
            sections_json_str = _resolve_sections_context(
                sections_path, is_latex, auto_sections_json, progress, task
            )

            # generate edits using core helper
            progress.update(task, description="Generating edits with AI...")
            edits = generate_edits_core(
                settings,
                lines,
                job_text,
                sections_json_str,
                model,
                risk_enum,
                on_error_policy,
                ui,
                persist_path=edits_json,
            )
            progress.advance(task)

            # persist edits (for inspection / re-run)
            if edits is None:
                from ...core.exceptions import EditError

                raise EditError("Failed to generate valid edits")
            persist_edits_json(edits, edits_json, progress, task)

            # apply edits using core helper
            progress.update(task, description="Applying edits...")
            if edits is None:
                from ...core.exceptions import EditError

                raise EditError("Failed to generate valid edits")
            new_lines = apply_edits_core(
                settings,
                lines,
                edits,
                risk_enum,
                on_error_policy,
                ui,
                interactive_mode,
                job_text=job_text,
                sections_json=sections_json_str,
                model=model,
                persist_special_ops=interactive_mode,
                edits_json_path=edits_json,
                resume_path=resume,
                descriptor=descriptor,
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

    # generate results report by mode
    if apply:
        report_result(
            "apply",
            settings=settings,
            output_path=output_resume,
            preserve_formatting=preserve_formatting,
            preserve_mode=preserve_mode,
        )
    elif edits_only:
        report_result("edits", edits_path=edits_json)
    else:
        report_result(
            "tailor",
            settings=settings,
            edits_path=edits_json,
            output_path=output_resume,
        )
