# src/cli/commands/sectionize.py
# Sectionize command for parsing resume into structured sections using AI

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer

from ...ai.prompts import build_sectionizer_prompt
from ...ai.clients import run_generate
from ...ai.utils import normalize_sections_response
from ...loom_io import (
    read_resume,
    write_json_safe,
    detect_template,
    analyze_latex,
    sections_to_payload,
    number_lines,
)
from ...core.exceptions import handle_loom_error

from ..app import app
from ..helpers import handle_help_flag, validate_required_args
from ...ui.core.progress import setup_ui_with_progress
from ...ui.display.reporting import report_result
from ..logic import ArgResolver
from ..params import ResumeArg, OutJsonOpt, ModelOpt
from ...ui.help.help_data import command_help
from ...config.settings import get_settings


# * Parse resume document into structured sections using AI sectionizer
@command_help(
    name="sectionize",
    description="Parse resume document into structured sections using AI",
    long_description=(
        "analyze resume (.docx or .tex) & identify distinct sections such as "
        "SUMMARY, EXPERIENCE & EDUCATION. Produce machine-readable JSON map "
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
    resume_path: Optional[Path] = ResumeArg(),
    out_json: Optional[Path] = OutJsonOpt(),
    model: Optional[str] = ModelOpt(),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message & exit."),
) -> None:
    handle_help_flag(ctx, help, "sectionize")
    settings = get_settings(ctx)
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

    # validate required arguments (model not required for LaTeX path)
    required_args = {
        "resume_path": (resume_path, "Resume path"),
        "out_json": (
            out_json,
            "Output path (provide --out-json or set sections_path in config)",
        ),
    }
    resume_suffix = resume_path.suffix.lower() if resume_path else ""
    if resume_suffix != ".tex":
        required_args["model"] = (model, "Model (provide --model or set in config)")

    validate_required_args(**required_args)

    # type assertions after validation
    assert resume_path is not None
    assert out_json is not None

    is_latex = resume_path.suffix.lower() == ".tex"
    if not is_latex:
        assert model is not None
    total_steps = 3 if is_latex else 4

    with setup_ui_with_progress("Processing resume...", total=total_steps) as (
        ui,
        progress,
        task,
    ):
        progress.update(task, description="Reading resume document...")
        lines = read_resume(resume_path)
        progress.advance(task)

        if is_latex:
            progress.update(task, description="Analyzing LaTeX structure...")
            resume_text = resume_path.read_text(encoding="utf-8")
            descriptor = detect_template(resume_path, resume_text)
            analysis = analyze_latex(lines, descriptor)
            payload = sections_to_payload(analysis)
            progress.advance(task)

            progress.update(task, description="Writing sections JSON...")
            write_json_safe(payload, out_json)
            progress.advance(task)
        else:
            progress.update(task, description="Numbering lines...")
            numbered = number_lines(lines)
            progress.advance(task)

            progress.update(task, description="Building prompt and calling OpenAI...")
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
            # normalize short keys (k->kind, h->heading_text, etc.) to full keys
            data = normalize_sections_response(data)
            progress.advance(task)

            progress.update(task, description="Writing sections JSON...")
            write_json_safe(data, out_json)
            progress.advance(task)

    report_result("sections", sections_path=out_json)
