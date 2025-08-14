# src/cli/commands/apply.py
# Apply command for executing edits.json operations on resume documents

from __future__ import annotations

from pathlib import Path
import typer

from ...core.constants import RiskLevel, ValidationPolicy
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import (
    setup_ui_with_progress,
    load_edits_json,
    report_result,
    validate_required_args,
    write_output_with_diff,
)
from ..logic import ArgResolver, apply_edits_core
from ..params import (
    ResumeArg,
    EditsJsonOpt,
    OutputResumeOpt,
    RiskOpt,
    OnErrorOpt,
    PreserveFormattingOpt,
    PreserveModeOpt,
)
from ...loom_io import read_docx


# * Apply edits from JSON to resume document & generate tailored output
@app.command()
@handle_loom_error
def apply(
    ctx: typer.Context,
    resume: Path | None = ResumeArg(),
    edits_json: Path | None = EditsJsonOpt(),
    output_resume: Path | None = OutputResumeOpt(),
    risk: RiskLevel | None = RiskOpt(),
    on_error: ValidationPolicy | None = OnErrorOpt(),
    preserve_formatting: bool = PreserveFormattingOpt(),
    preserve_mode: str = PreserveModeOpt(),
) -> None:
    settings = ctx.obj
    resolver = ArgResolver(settings)

    # resolve arguments w/ settings defaults
    common_resolved = resolver.resolve_common(resume=resume, edits_json=edits_json)
    path_resolved = resolver.resolve_paths(output_resume=output_resume)
    option_resolved = resolver.resolve_options(risk=risk, on_error=on_error)

    resume = common_resolved["resume"]
    edits_json, output_resume = (
        common_resolved["edits_json"],
        path_resolved["output_resume"],
    )
    risk, on_error = option_resolved["risk"], option_resolved["on_error"]

    # validate required arguments
    validate_required_args(
        resume=(resume, "Resume path"),
        edits_json=(edits_json, "Edits path"),
        output_resume=(output_resume, "Output path"),
    )

    # type assertions after validation
    assert resume is not None
    assert edits_json is not None
    assert output_resume is not None

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
        new_lines = apply_edits_core(settings, lines, edits_obj, risk, on_error, ui)
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
        "apply",
        settings=settings,
        output_path=output_resume,
        preserve_formatting=preserve_formatting,
        preserve_mode=preserve_mode,
    )

