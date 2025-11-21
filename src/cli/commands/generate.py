# src/cli/commands/generate.py
# Generate command for creating edits.json w/ AI-powered resume tailoring

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import validate_required_args
from ...ui.core.progress import (
    setup_ui_with_progress,
    load_resume_and_job,
    load_sections,
)
from ...ui.display.reporting import persist_edits_json, report_result
from ..logic import ArgResolver, generate_edits_core
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
    # detect help flag & show custom help
    if help:
        from .help import show_command_help

        show_command_help("generate")
        ctx.exit()
    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    # resolve arguments w/ settings defaults
    common_resolved = resolver.resolve_common(
        model=model,
        edits_json=edits_json,
        sections_path=sections_path,
        resume=resume,
        job=job,
    )
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)

    model, edits_json, sections_path, resume, job = (
        common_resolved["model"],
        common_resolved["edits_json"],
        common_resolved["sections_path"],
        common_resolved["resume"],
        common_resolved["job"],
    )
    risk_enum: RiskLevel = option_resolved["risk"]
    on_error_policy: ValidationPolicy = option_resolved["on_error"]

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
            persist_path=edits_json,
        )
        progress.advance(task)

        # write edits
        persist_edits_json(edits, edits_json, progress, task)

    report_result("edits", edits_path=edits_json)
