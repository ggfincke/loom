# src/cli/commands/init.py
# Initialize a resume workspace from a Loom template

from __future__ import annotations

from pathlib import Path
from typing import Optional
import shutil
import typer

from ...loom_io.console import console
from ..decorators import handle_loom_error
from ..app import app
from ...ui.help.help_data import command_help
from .templates import discover_templates


@command_help(
    name="init",
    description="Initialize a resume workspace from a template",
    examples=[
        "loom init --template swe-latex",
        "loom init --template swe-latex --output my-resume",
    ],
    see_also=["templates"],
)
@app.command(name="init", help="Initialize a resume workspace from a template")
@handle_loom_error
def init_template(
    template: str = typer.Option(..., "--template", "-t", help="Template id to copy"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Destination directory (defaults to ./resume)"
    ),
) -> None:
    templates = discover_templates()
    selected = None
    for descriptor_path, descriptor in templates:
        if descriptor.id == template:
            selected = (descriptor_path, descriptor)
            break
    if selected is None:
        raise typer.BadParameter(
            f"Template '{template}' not found. Run 'loom templates' to list options."
        )

    descriptor_path, descriptor = selected
    template_dir = descriptor_path.parent
    target_dir = output or (Path.cwd() / "resume")

    if target_dir.resolve() == template_dir.resolve():
        raise typer.BadParameter("Output path cannot be the template source directory")

    if target_dir.exists() and any(target_dir.iterdir()):
        raise typer.BadParameter(f"Output directory {target_dir} is not empty")

    shutil.copytree(template_dir, target_dir, dirs_exist_ok=True)
    console.print(f"[green]Initialized template[/] '{descriptor.id}' at {target_dir}")
