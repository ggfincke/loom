# src/cli/commands/config.py
# Settings mgmt subcommands for Loom CLI (list/get/set/reset/path) w/ JSON-backed storage

from __future__ import annotations

import json
from dataclasses import fields
from typing import Any
import typer
from builtins import list as builtin_list

from ...config.settings import settings_manager, LoomSettings
from ...loom_io.console import console
from ...ui.theming.theme_definitions import THEMES
from ...ui.theming.theme_engine import (
    styled_checkmark,
    success_gradient,
    accent_gradient,
)
from ...ui.theming.styled_helpers import (
    styled_setting_line,
    format_setting_value,
    styled_success_line,
)
from ..app import app
from ..helpers import handle_help_flag
from ...ui.theming.theme_selector import interactive_theme_selector
from ...ui.display.ascii_art import show_loom_art
from ...ui.help.help_data import command_help

# * Sub-app for config commands; registered on root app
config_app = typer.Typer(
    rich_markup_mode="rich", help="[loom.accent2]Manage Loom settings[/]"
)
app.add_typer(config_app, name="config")


# concise set of known keys for validation
def _known_keys() -> set[str]:
    return {f.name for f in fields(LoomSettings)}


# valid theme names
def _valid_themes() -> set[str]:
    return set(THEMES.keys())


# coerce string value to JSON value (numbers, bools, null) or keep raw string
def _coerce_value(
    raw: str,
) -> str | int | float | bool | None | builtin_list[Any] | dict[str, Any]:
    try:
        # parse JSON for numbers/bools/null/arrays/objects
        return json.loads(raw)
    except Exception:
        return raw


# * default callback: show current settings w/ styled output when no subcommand provided
@command_help(
    name="config",
    description="Manage Loom settings & configuration",
    long_description=(
        "Configure default directories, file names, AI model, and visual theme. "
        "Settings persist to ~/.loom/config.json and are used when CLI arguments "
        "are omitted."
    ),
    examples=[
        "loom config  # Show all current settings",
        "loom config set model gpt-4o  # Set default AI model",
        "loom config set data_dir /path/to/job_applications",
        "loom config set resume_filename my_resume.docx",
        "loom config themes  # Interactive theme selector",
        "loom config get model  # Get specific setting",
        "loom config reset  # Reset all to defaults",
        "loom config path  # Show config file location",
    ],
    see_also=["tailor"],
)
# * Print current settings & config path w/ styled output
def _print_current_settings() -> None:
    data = settings_manager.list_settings()

    # display header
    console.print()
    console.print(accent_gradient("Current Configuration"))
    console.print(f"[dim]Config file: {settings_manager.config_path}[/]")
    console.print()

    # display each setting w/ styled formatting
    for key, value in data.items():
        formatted_value = format_setting_value(value)
        console.print(*styled_setting_line(key, formatted_value))

    # add help usage note
    console.print()
    console.print(
        f"[dim]Use [/][loom.accent2]loom config --help[/][dim] to see available commands[/]"
    )


@config_app.callback(invoke_without_command=True)
def config_callback(
    ctx: typer.Context,
    help: bool = typer.Option(
        False, "--help", "-h", help="Show help message and exit."
    ),
) -> None:
    handle_help_flag(ctx, help, "config")

    if ctx.invoked_subcommand is None:
        _print_current_settings()


# * Get a specific setting value & print as JSON
@config_app.command()
def get(key: str) -> None:
    if key not in _known_keys():
        raise typer.BadParameter(f"Unknown setting: {key}")
    value = settings_manager.get(key)
    # print JSON for consistency (strings quoted)
    console.print(f"[loom.accent2]{json.dumps(value)}[/]")


# * Set a specific setting value; values are JSON-coerced when possible
@config_app.command(name="set")
def set_cmd(key: str, value: str) -> None:
    if key not in _known_keys():
        raise typer.BadParameter(f"Unknown setting: {key}")

    # special validation for theme setting
    if key == "theme" and value not in _valid_themes():
        valid_themes = ", ".join(sorted(_valid_themes()))
        raise typer.BadParameter(
            f"Invalid theme '{value}'. Valid themes: {valid_themes}"
        )

    coerced = _coerce_value(value)
    try:
        settings_manager.set(key, coerced)

        # refresh console theme if theme was changed
        if key == "theme":
            from ...loom_io.console import refresh_theme

            refresh_theme()

    except Exception as e:
        raise typer.BadParameter(str(e))
    console.print(
        *styled_success_line(f"Set {key}", f"[loom.accent2]{json.dumps(coerced)}[/]")
    )


# * Reset all settings to defaults
@config_app.command()
def reset() -> None:
    settings_manager.reset()
    console.print(styled_checkmark(), success_gradient("Reset settings to defaults"))


# * Show the configuration file path
@config_app.command()
def path() -> None:
    console.print(f"[loom.accent2]{settings_manager.config_path}[/]")


# * Explicit 'list' command to show current settings
@config_app.command()
# noqa: A003 - allow command name 'list'
def list() -> None:
    _print_current_settings()


# * Interactive theme selector w/ live preview
@config_app.command()
def themes() -> None:
    # run interactive selector
    selected_theme = interactive_theme_selector()

    if selected_theme:
        # save the new theme
        settings_manager.set("theme", selected_theme)
        from ...loom_io.console import refresh_theme

        refresh_theme()

        console.print()
        console.print(
            *styled_success_line("Theme set to", f"[loom.accent2]{selected_theme}[/]")
        )

        # show banner w/ new theme
        console.print("\n[loom.accent]New theme preview:[/]")
        show_loom_art()
    else:
        console.print("\n[dim]Theme selection cancelled[/]")
