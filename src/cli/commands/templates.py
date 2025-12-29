# src/cli/commands/templates.py
# Template management command for listing available LaTeX templates

from __future__ import annotations

from pathlib import Path
import typer

from ...loom_io import load_descriptor, TemplateDescriptor
from ..decorators import handle_loom_error
from ...loom_io.console import console
from ..app import app
from ...ui.help.help_data import command_help


# * Resolve path to bundled templates directory (if available)
def get_templates_root() -> Path | None:
    # Search multiple parent levels to support both dev & installed package structures
    candidates = [
        Path(__file__).resolve().parents[4] / "templates",  # installed package
        Path(__file__).resolve().parents[3] / "templates",  # editable install
        Path(__file__).resolve().parents[2] / "templates",  # development
        Path.cwd() / "templates",  # current directory fallback
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


# * Load all available template descriptors
def discover_templates() -> list[tuple[Path, TemplateDescriptor]]:
    root = get_templates_root()
    if root is None:
        return []
    templates: list[tuple[Path, TemplateDescriptor]] = []
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
        template_id = getattr(descriptor, "id", None) or getattr(
            descriptor, "inline_marker", "unknown"
        )
        name = getattr(descriptor, "name", None) or template_id or "Unnamed template"
        template_type = getattr(descriptor, "type", "resume")
        location = descriptor_path.parent
        console.print(
            f" - {template_id} ({template_type}) -> {name} [{location}]", markup=False
        )
