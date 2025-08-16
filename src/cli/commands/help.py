# src/cli/commands/help.py
# Help command for showing branded help screens for specific commands

from __future__ import annotations

import typer
from typing import Any

from ..app import app
from ...ui.help.help_renderer import HelpRenderer
from ...ui.help.help_data import COMMAND_HELP
from ...loom_io.console import console


# global help renderer instance
help_renderer = HelpRenderer()


# * show main application help screen
def show_main_help(app: typer.Typer) -> None:
    help_renderer.render_main_help(app)


# * show help for specific command
def show_command_help(command_name: str, command: Any = None) -> None:
    help_renderer.render_command_help(command_name, command)


# * Show detailed help for specific command
@app.command()
def help(
    command: str | None = typer.Argument(None, help="Command to show help for"),
) -> None:
    
    if command is None:
        console.print("[red]Please specify a command name.[/]")
        console.print("Available commands:", ", ".join(COMMAND_HELP.keys()))
        return
    
    if command not in COMMAND_HELP:
        console.print(f"[red]Unknown command: {command}[/]")
        console.print("Available commands:", ", ".join(COMMAND_HELP.keys()))
        return
    
    show_command_help(command)