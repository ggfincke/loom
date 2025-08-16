# src/cli/commands/plan.py
# Plan command for generating edits w/ step-by-step planning workflow

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
)
from ..logic import ArgResolver, generate_edits_core
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
    resume: Path | None = ResumeArg(),
    job: Path | None = JobArg(),
    edits_json: Path | None = EditsJsonOpt(),
    plan: int | None = PlanOpt(),
    risk: RiskLevel | None = RiskOpt(),
    on_error: ValidationPolicy | None = OnErrorOpt(),
    model: str | None = ModelOpt(),
    sections_path: Path | None = SectionsPathOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & show custom help
    if help:
        from .help import show_command_help
        show_command_help("plan")
        ctx.exit()
    settings = ctx.obj
    resolver = ArgResolver(settings)

    # resolve args w/ defaults
    common_resolved = resolver.resolve_common(
        resume=resume, job=job, edits_json=edits_json, model=model, sections_path=sections_path
    )
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)

    resume, job, edits_json = (
        common_resolved["resume"],
        common_resolved["job"],
        common_resolved["edits_json"],
    )
    model, sections_path = (
        common_resolved["model"],
        common_resolved["sections_path"],
    )
    risk_enum: RiskLevel = option_resolved["risk"]
    on_error_policy: ValidationPolicy = option_resolved["on_error"]

    # unused but planned
    _ = plan

    # validate required arguments
    validate_required_args(
        resume=(resume, "Resume path"),
        job=(job, "Job description path"),
        model=(model, "Model (provide --model or set in config)"),
    )

    # type assertions after validation
    assert resume is not None
    assert job is not None
    assert edits_json is not None
    assert model is not None

    with setup_ui_with_progress("Planning edits...", total=5) as (
        ui,
        progress,
        task,
    ):
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

        persist_edits_json(edits, edits_json, progress, task)

        # create simple plan file
        progress.update(task, description="Writing plan...")
        from ...loom_io import ensure_parent

        ensure_parent(settings.plan_path)
        settings.plan_path.write_text("# Plan\n\n- single-shot (stub)\n", encoding="utf-8")
        progress.advance(task)

    report_result("plan", settings=settings, edits_path=edits_json)

