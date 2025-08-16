# src/cli/commands/tailor.py
# Tailor command for complete end-to-end resume tailoring workflow

from __future__ import annotations

from pathlib import Path
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error
from ...core.debug import enable_debug, disable_debug

from ..app import app
from ..helpers import validate_required_args
from ...ui.progress import setup_ui_with_progress, load_resume_and_job, load_sections
from ...ui.reporting import persist_edits_json, report_result, write_output_with_diff
from ..logic import ArgResolver, generate_edits_core, apply_edits_core
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
)


# * Complete end-to-end resume tailoring: generate edits & apply to create tailored resume
@command_help(
    name="tailor",
    description="Complete end-to-end resume tailoring: generate edits & apply in one step",
    long_description=(
        "Runs generation and apply in one pass: analyzes the job description, "
        "produces edits, then writes a tailored resume. Accepts the same safety "
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
@app.command(help="Complete end-to-end resume tailoring: generate edits & apply in one step")
@handle_loom_error
def tailor(
    ctx: typer.Context,
    job: Path | None = JobArg(),
    resume: Path | None = ResumeArg(),
    model: str | None = ModelOpt(),
    sections_path: Path | None = SectionsPathOpt(),
    edits_json: Path | None = EditsJsonOpt(),
    output_resume: Path | None = OutputResumeOpt(),
    risk: RiskLevel | None = RiskOpt(),
    on_error: ValidationPolicy | None = OnErrorOpt(),
    preserve_formatting: bool = PreserveFormattingOpt(),
    preserve_mode: str = PreserveModeOpt(),
    edits_only: bool = typer.Option(False, "--edits-only", help="Generate edits JSON only (don't apply)"),
    apply: bool = typer.Option(False, "--apply", help="Apply existing edits JSON to resume"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug output"),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & show custom help
    if help:
        from .help import show_command_help
        show_command_help("tailor")
        ctx.exit()
    
    # enable debug mode if verbose flag is set
    if verbose:
        enable_debug()
    else:
        disable_debug()
    
    # validate mutually exclusive flags
    if edits_only and apply:
        from ...loom_io.console import console
        console.print("[red]Error: --edits-only and --apply are mutually exclusive[/]")
        ctx.exit(1)
    
    settings = ctx.obj
    resolver = ArgResolver(settings)

    # resolve args w/ settings defaults
    common_resolved = resolver.resolve_common(
        job=job,
        resume=resume,
        model=model,
        sections_path=sections_path,
        edits_json=edits_json,
    )
    path_resolved = resolver.resolve_paths(output_resume=output_resume)
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

    # validate required arguments based on mode
    if apply:
        # apply mode: only need resume, edits_json, output_resume
        validate_required_args(
            resume=(resume, "Resume path"),
            output_resume=(
                output_resume,
                "Output resume path (provide argument or set output_dir in config)",
            ),
        )
    elif edits_only:
        # edits-only mode: need job, resume, model (no output_resume required)
        validate_required_args(
            job=(job, "Job description path"),
            resume=(resume, "Resume path"),
            model=(model, "Model (provide --model or set in config)"),
        )
    else:
        # full tailor mode: need everything
        validate_required_args(
            job=(job, "Job description path"),
            resume=(resume, "Resume path"),
            model=(model, "Model (provide --model or set in config)"),
            output_resume=(
                output_resume,
                "Output resume path (provide argument or set output_dir in config)",
            ),
        )

    # type assertions after validation
    assert resume is not None
    assert edits_json is not None
    
    if not apply:
        # job & model required for generation modes
        assert job is not None
        assert model is not None
    
    if not edits_only:
        # output_resume required for application modes
        assert output_resume is not None

    if apply:
        # apply mode: read existing edits & apply to resume
        assert output_resume is not None
        
        from ...loom_io import read_docx
        from ...ui.progress import load_edits_json
        
        with setup_ui_with_progress("Applying edits...", total=5) as (
            ui,
            progress,
            task,
        ):
            # read resume
            progress.update(task, description="Reading resume document...")
            lines = read_docx(resume)
            progress.advance(task)

            # read edits
            edits_obj = load_edits_json(edits_json, progress, task)

            # apply edits using core helper
            progress.update(task, description="Applying edits...")
            new_lines = apply_edits_core(settings, lines, edits_obj, risk_enum, on_error_policy, ui)
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
        # edits-only mode: generate edits but don't apply
        assert job is not None
        assert model is not None
        
        with setup_ui_with_progress("Generating edits...", total=4) as (
            ui,
            progress,
            task,
        ):
            # read resume + job
            lines, job_text = load_resume_and_job(resume, job, progress, task)

            # load optional sections
            sections_json_str = load_sections(sections_path, progress, task)

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
            )
            progress.advance(task)

            # write edits
            persist_edits_json(edits, edits_json, progress, task)
            
    else:
        # full tailor mode: generate edits & apply
        assert job is not None
        assert model is not None
        assert output_resume is not None
        
        with setup_ui_with_progress("Tailoring resume...", total=6) as (
            ui,
            progress,
            task,
        ):
            # read resume + job
            lines, job_text = load_resume_and_job(resume, job, progress, task)

            # load optional sections
            sections_json_str = load_sections(sections_path, progress, task)

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
            )
            progress.advance(task)

            # persist edits (for inspection / re-run)
            persist_edits_json(edits, edits_json, progress, task)

            # apply edits using core helper
            progress.update(task, description="Applying edits...")
            new_lines = apply_edits_core(
                settings, lines, edits, risk_enum, on_error_policy, ui
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

    # report results based on mode
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
            "tailor", settings=settings, edits_path=edits_json, output_path=output_resume
        )

