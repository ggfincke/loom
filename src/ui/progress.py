# src/ui/progress.py
# UI progress bar setup & management utilities for consistent CLI progress display

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from ..loom_io import read_docx, read_text, read_json_safe
from ..loom_io.types import Lines
from . import UI


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