# src/cli/helpers.py
# Shared CLI helpers for validation, progress, I/O orchestration, and reporting

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from ..config.settings import LoomSettings
from ..loom_io import (
    read_docx,
    number_lines,
    read_text,
    write_docx,
    apply_edits_to_docx,
    write_json_safe,
    read_json_safe,
    ensure_parent,
)
from ..loom_io.console import console
from ..loom_io.types import Lines
from ..core.pipeline import diff_lines
from ..ui.colors import styled_checkmark, styled_arrow, LoomColors, success_gradient
from ..ui import UI
import typer


# * validate required CLI arguments & raise typer.BadParameter if missing
def validate_required_args(**kwargs) -> None:
    for _, (value, description) in kwargs.items():
        if not value:
            raise typer.BadParameter(
                f"{description} is required (provide argument or set in config)"
            )


# * context manager to build UI progress & yield (ui, progress, task)
@contextmanager
def setup_ui_with_progress(task_description: str, total: int):
    ui = UI()
    with ui.build_progress() as progress:
        ui.progress = progress
        task = progress.add_task(task_description, total=total)
        yield ui, progress, task


# read resume lines & job text w/ progress updates
def load_resume_and_job(
    resume_path: Path, job_path: Path, progress, task
) -> tuple[Lines, str]:
    progress.update(task, description="Reading resume document...")
    lines = read_docx(resume_path)
    progress.advance(task)

    progress.update(task, description="Reading job description...")
    job_text = read_text(job_path)
    progress.advance(task)

    return lines, job_text


# load sections JSON string if available
def load_sections(sections_path: Path | None, progress, task) -> str | None:
    progress.update(task, description="Loading sections data...")
    sections_json_str = None
    if sections_path and Path(sections_path).exists():
        sections_json_str = Path(sections_path).read_text(encoding="utf-8")
    progress.advance(task)
    return sections_json_str


# load edits JSON object from file
def load_edits_json(edits_path: Path, progress, task) -> dict:
    progress.update(task, description="Loading edits JSON...")
    edits_obj = read_json_safe(edits_path)
    progress.advance(task)
    return edits_obj


def persist_edits_json(
    edits: dict, out_path: Path, progress, task, description: str = "Writing edits JSON..."
) -> None:
    # persist edits JSON to disk w/ progress update
    progress.update(task, description=description)
    write_json_safe(edits, out_path)
    progress.advance(task)


# * Report results consistently across commands to the console
def report_result(result_type: str, settings: LoomSettings | None = None, **paths) -> None:
    checkmark = styled_checkmark()
    arrow = styled_arrow()
    
    if result_type == "sections":
        console.print(checkmark, success_gradient("Wrote sections to"), f"{paths['sections_path']}")
    elif result_type == "edits":
        console.print(checkmark, success_gradient("Wrote edits"), arrow, f"{paths['edits_path']}")
    elif result_type == "tailor":
        console.print(checkmark, success_gradient("Complete tailoring finished"))
        console.print(f"   Edits {arrow} {paths['edits_path']}", style="loom.accent2")
        console.print(f"   Resume {arrow} {paths['output_path']}", style="loom.accent2") 
        if settings:
            console.print(f"   Diff {arrow} {settings.diff_path}", style="progress.path")
    elif result_type == "apply":
        format_msg = (
            f" (formatting preserved via {paths.get('preserve_mode', 'unknown')} mode)"
            if paths.get("preserve_formatting")
            else " (plain text)"
        )
        console.print(checkmark, success_gradient(f"Wrote DOCX{format_msg}"), arrow, f"{paths['output_path']}")
        if settings:
            console.print(checkmark, f"Diff {arrow} {settings.diff_path}", style="loom.accent2")
    elif result_type == "plan":
        console.print(checkmark, success_gradient("Wrote edits"), arrow, f"{paths['edits_path']}")
        if settings:
            console.print(checkmark, f"Plan {arrow} {settings.plan_path}", style="loom.accent2")


# * Generate diff & write tailored resume output w/ formatting preservation
def write_output_with_diff(
    settings: LoomSettings,
    resume_path: Path,
    resume_lines: Lines,
    new_lines: Lines,
    output_path: Path,
    preserve_formatting: bool,
    preserve_mode: str,
    progress,
    task,
) -> None:
    # generate diff
    progress.update(task, description="Generating diff...")
    diff = diff_lines(resume_lines, new_lines)
    ensure_parent(settings.diff_path)
    settings.diff_path.write_text(diff, encoding="utf-8")
    progress.advance(task)

    # write output
    progress.update(task, description="Writing tailored resume...")
    if preserve_formatting:
        apply_edits_to_docx(
            resume_path, new_lines, output_path, preserve_mode=preserve_mode
        )
    else:
        write_docx(new_lines, output_path)
    progress.advance(task)

