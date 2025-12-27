# src/ui/display/reporting.py
# Result reporting utilities for consistent CLI output formatting

from __future__ import annotations

from pathlib import Path

from ...config.settings import LoomSettings
from ...loom_io import (
    write_json_safe,
    apply_edits_to_docx,
    write_docx,
    write_text_lines,
    ensure_parent,
)
from ...loom_io.console import console
from ...loom_io.types import Lines
from ...core.pipeline import diff_lines
from ...core.exceptions import LaTeXError
from ..theming.theme_engine import styled_checkmark, styled_arrow, success_gradient


def _print_success_line(label: str, path: str | Path | None = None) -> None:
    # Print styled success line: checkmark + gradient label [+ arrow + path].
    checkmark = styled_checkmark()
    if path is not None:
        arrow = styled_arrow()
        console.print(checkmark, success_gradient(label), arrow, f"{path}")
    else:
        console.print(checkmark, success_gradient(label))


def persist_edits_json(
    edits: dict,
    out_path: Path,
    progress,
    task,
    description: str = "Writing edits JSON...",
) -> None:
    # persist edits JSON to disk w/ progress update
    progress.update(task, description=description)
    write_json_safe(edits, out_path)
    progress.advance(task)


# * Report results consistently across commands to the console
def report_result(
    result_type: str, settings: LoomSettings | None = None, **paths
) -> None:
    arrow = styled_arrow()

    if result_type == "sections":
        _print_success_line("Wrote sections to", paths["sections_path"])
    elif result_type == "edits":
        _print_success_line("Wrote edits", paths["edits_path"])
    elif result_type == "tailor":
        _print_success_line("Complete tailoring finished")
        console.print(f"   Edits {arrow} {paths['edits_path']}", style="loom.accent2")
        console.print(f"   Resume {arrow} {paths['output_path']}", style="loom.accent2")
        if settings:
            console.print(
                f"   Diff {arrow} {settings.diff_path}", style="progress.path"
            )
    elif result_type == "apply":
        out_path = Path(paths["output_path"])
        if out_path.suffix.lower() == ".docx":
            format_msg = (
                f" (formatting preserved via {paths.get('preserve_mode', 'unknown')} mode)"
                if paths.get("preserve_formatting")
                else " (plain text)"
            )
            _print_success_line(f"Wrote DOCX{format_msg}", out_path)
        else:
            _print_success_line("Wrote text", out_path)
        if settings:
            checkmark = styled_checkmark()
            console.print(
                checkmark, f"Diff {arrow} {settings.diff_path}", style="loom.accent2"
            )
    elif result_type == "plan":
        _print_success_line("Wrote edits", paths["edits_path"])
        if settings:
            checkmark = styled_checkmark()
            console.print(
                checkmark, f"Plan {arrow} {settings.plan_path}", style="loom.accent2"
            )


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
    try:
        output_suffix = output_path.suffix.lower()
        resume_suffix = resume_path.suffix.lower()

        if output_suffix == ".docx":
            # formatting preservation only works w/ DOCX input & output
            if preserve_formatting and resume_suffix == ".docx":
                apply_edits_to_docx(
                    resume_path, new_lines, output_path, preserve_mode=preserve_mode
                )
            else:
                write_docx(new_lines, output_path)
        else:
            # for .tex files, write as text (loom doesn't compile LaTeX)
            write_text_lines(new_lines, output_path)
            if output_suffix == ".tex":
                console.print(
                    f"[yellow]Note: LaTeX file written as text to {output_path}[/]"
                )
                console.print(
                    "[dim]To compile LaTeX: run 'pdflatex', 'xelatex', or 'lualatex' on the output file[/]"
                )
        progress.advance(task)
    except Exception as e:
        if "Package not found" in str(e) or "LaTeX" in str(e):
            raise LaTeXError(
                f"LaTeX processing error: {e}\n"
                f"This appears to be a LaTeX compilation issue, not a loom error.\n"
                f"Check that all required LaTeX packages are installed & accessible."
            )
        else:
            raise  # re-raise non-LaTeX errors as-is
