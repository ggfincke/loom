# src/cli/commands/help.py
# Help command for showing branded help screens for specific commands

from __future__ import annotations

import typer
from typing import Any

from ..app import app
from ...ui.help.help_renderer import HelpRenderer
from ...ui.help.help_data import (
    get_command_metadata,
    get_all_command_metadata,
)
from ...loom_io.console import console


# Global help renderer instance
help_renderer = HelpRenderer()


# * Show main application help screen
def show_main_help(app: typer.Typer) -> None:
    help_renderer.render_main_help(app)


# * Show help for specific command
def show_command_help(command_name: str, command: Any = None) -> None:
    help_renderer.render_command_help(command_name, command)


# * Show detailed help for specific command
@app.command()
def help(
    command: str | None = typer.Argument(None, help="Command to show help for"),
) -> None:
    # prefer metadata registry for listing & validation
    if command is None:
        available = sorted(get_all_command_metadata().keys())
        console.print("Available commands:", ", ".join(available))
        return

    # validate command existence using metadata registry
    if not get_command_metadata(command):
        available = sorted(get_all_command_metadata().keys())
        console.print(f"[red]Unknown command: {command}[/]")
        console.print("Available commands:", ", ".join(available))
        return

    show_command_help(command)
