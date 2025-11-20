# src/cli/commands/templates.py
# Template management command for listing available LaTeX templates

from __future__ import annotations

from pathlib import Path
import typer

from ...core.exceptions import handle_loom_error
from ...loom_io import load_descriptor, TemplateDescriptor
from ...loom_io.console import console
from ..app import app
from ...ui.help.help_data import command_help


# * Resolve path to bundled templates directory
def get_templates_root() -> Path:
    candidates = [
        Path(__file__).resolve().parents[3] / "templates",
        Path(__file__).resolve().parents[2] / "templates",
        Path.cwd() / "templates",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise typer.BadParameter("No templates directory found. Ensure templates are bundled with Loom.")


# * Load all available template descriptors
def discover_templates() -> list[tuple[Path, TemplateDescriptor]]:
    root = get_templates_root()
    templates: list[tuple[Path, object]] = []
    for descriptor_path in sorted(root.rglob("loom-template.toml")):
        try:
            descriptor = load_descriptor(descriptor_path)
            templates.append((descriptor_path, descriptor))
        except Exception as e:
            console.print(f"[red]Skipping {descriptor_path}: {e}[/]")
    return templates


@command_help(
    name="templates",
    description="List available Loom templates",
    examples=["loom templates"],
    see_also=["init"],
)
@app.command(name="templates", help="List available Loom templates")
@handle_loom_error
def list_templates() -> None:
    templates = discover_templates()
    if not templates:
        console.print("[yellow]No templates found[/]")
        return

    console.print("[green]Available templates:[/]")
    for descriptor_path, descriptor in templates:
        template_id = getattr(descriptor, "id", None) or getattr(descriptor, "inline_marker", "unknown")
        name = getattr(descriptor, "name", None) or template_id or "Unnamed template"
        template_type = getattr(descriptor, "type", "resume")
        location = descriptor_path.parent
        console.print(f" - {template_id} ({template_type}) -> {name} [{location}]")
