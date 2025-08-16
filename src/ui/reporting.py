# src/ui/reporting.py
# Result reporting utilities for consistent CLI output formatting

from __future__ import annotations

from pathlib import Path

from ..config.settings import LoomSettings
from ..loom_io import write_json_safe, apply_edits_to_docx, write_docx, ensure_parent
from ..loom_io.console import console
from ..loom_io.types import Lines
from ..core.pipeline import diff_lines
from .colors import styled_checkmark, styled_arrow, success_gradient


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