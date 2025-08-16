# src/cli/commands/sectionize.py
# Sectionize command for parsing resume into structured sections using AI

from __future__ import annotations

from pathlib import Path
import typer

from ...ai.prompts import build_sectionizer_prompt
from ...ai.clients import run_generate
from ...loom_io import read_docx, number_lines, write_json_safe
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import validate_required_args
from ...ui.progress import setup_ui_with_progress
from ...ui.reporting import report_result
from ..logic import ArgResolver
from ..params import ResumeArg, OutJsonOpt, ModelOpt
from ...ui.help.help_data import command_help


# * Parse resume document into structured sections using AI sectionizer
@command_help(
    name="sectionize",
    description="Parse resume document into structured sections using AI",
    long_description=(
        "Analyzes your resume (.docx) and identifies distinct sections such as "
        "SUMMARY, EXPERIENCE, and EDUCATION. Produces a machine-readable JSON map "
        "used to target edits precisely in later steps.\n\n"
        "Defaults: paths come from config when omitted (see 'loom config')."
    ),
    examples=[
        "loom sectionize resume.docx --out-json sections.json",
        "loom sectionize my_resume.docx  # uses config defaults",
        "loom sectionize resume.docx --model gpt-4o-mini",
    ],
    see_also=["tailor", "config"],
)
@app.command(help="Parse resume document into structured sections using AI")
@handle_loom_error
def sectionize(
    ctx: typer.Context,
    resume_path: Path | None = ResumeArg(),
    out_json: Path | None = OutJsonOpt(),
    model: str | None = ModelOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & show custom help
    if help:
        from .help import show_command_help
        show_command_help("sectionize")
        ctx.exit()
    settings = ctx.obj
    resolver = ArgResolver(settings)

    # resolve arguments w/ settings defaults
    resolved = resolver.resolve_common(
        resume=resume_path, out_json=out_json, model=model
    )
    resume_path, out_json, model = (
        resolved["resume"],
        resolved["out_json"],
        resolved["model"],
    )

    # validate required arguments
    validate_required_args(
        resume_path=(resume_path, "Resume path"),
        out_json=(
            out_json,
            "Output path (provide --out-json or set sections_path in config)",
        ),
        model=(model, "Model (provide --model or set in config)"),
    )

    # type assertions after validation
    assert resume_path is not None
    assert out_json is not None
    assert model is not None

    with setup_ui_with_progress("Processing resume...", total=4) as (
        ui,
        progress,
        task,
    ):
        progress.update(task, description="Reading resume document...")
        lines = read_docx(resume_path)
        progress.advance(task)

        progress.update(task, description="Numbering lines...")
        numbered = number_lines(lines)
        progress.advance(task)

        progress.update(
            task, description="Building prompt and calling OpenAI..."
        )
        prompt = build_sectionizer_prompt(numbered)
        result = run_generate(prompt, model=model)

        # handle JSON parsing errors
        if not result.success:
            from ...core.exceptions import AIError

            raise AIError(
                f"AI failed to generate valid JSON: {result.error}\n\nRaw response:\n{result.raw_text}\n\nExtracted JSON:\n{result.json_text}"
            )

        data = result.data
        assert data is not None, "Expected non-None data from successful AI result"
        progress.advance(task)

        progress.update(task, description="Writing sections JSON...")
        write_json_safe(data, out_json)
        progress.advance(task)

    report_result("sections", sections_path=out_json)

