# src/cli/commands/tailor.py
# Tailor command for complete end-to-end resume tailoring workflow

from __future__ import annotations

from pathlib import Path
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import (
    setup_ui_with_progress,
    load_resume_and_job,
    load_sections,
    persist_edits_json,
    report_result,
    validate_required_args,
    write_output_with_diff,
)
from ..logic import ArgResolver, generate_edits_core, apply_edits_core
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
@app.command()
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
) -> None:
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

    # validate required arguments
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
    assert job is not None
    assert resume is not None
    assert edits_json is not None
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

    report_result(
        "tailor", settings=settings, edits_path=edits_json, output_path=output_resume
    )

