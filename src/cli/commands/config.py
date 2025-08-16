# src/cli/commands/config.py
# Settings mgmt subcommands for Loom CLI (list/get/set/reset/path) w/ JSON-backed storage

from __future__ import annotations

import json
from dataclasses import fields
import typer

from ...config.settings import settings_manager, LoomSettings
from ...loom_io.console import console
from ...ui.colors import styled_checkmark, success_gradient, LoomColors, THEMES, accent_gradient, styled_bullet, styled_arrow
from ..app import app
from ...ui.theme_selector import interactive_theme_selector
from ...ui.ascii_art import show_loom_art

# * Sub-app for config commands; registered on root app
config_app = typer.Typer(
    rich_markup_mode="rich", 
    help="[loom.accent2]Manage Loom settings[/]"
)
app.add_typer(config_app, name="config")

# concise set of known keys for validation
def _known_keys() -> set[str]:
    return {f.name for f in fields(LoomSettings)}

# valid theme names
def _valid_themes() -> set[str]:
    return set(THEMES.keys())

# coerce string value to JSON value (numbers, bools, null) or keep raw string
def _coerce_value(raw: str):
    try:
        # parse JSON for numbers/bools/null/arrays/objects
        return json.loads(raw)
    except Exception:
        return raw

# * default callback: show current settings w/ styled output when no subcommand provided
@config_app.callback(invoke_without_command=True)
def config_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & show custom help
    if help:
        from .help import show_command_help
        show_command_help("config")
        ctx.exit()
    
    if ctx.invoked_subcommand is None:
        data = settings_manager.list_settings()
        
        # display header
        console.print()
        console.print(accent_gradient("Current Configuration"))
        console.print(f"[dim]Config file: {settings_manager.config_path}[/]")
        console.print()
        
        # display each setting w/ styled formatting
        for key, value in data.items():
            # format value based on type
            if isinstance(value, str):
                formatted_value = f'[loom.accent2]"{value}"[/]'
            elif isinstance(value, bool):
                formatted_value = f'[loom.accent2]{str(value).lower()}[/]'
            elif isinstance(value, (int, float)):
                formatted_value = f'[loom.accent2]{value}[/]'
            else:
                formatted_value = f'[loom.accent2]{json.dumps(value)}[/]'
            
            # display setting w/ bullet & arrow styling
            console.print(
                styled_bullet(),
                f"[bold white]{key}[/]",
                "[loom.accent2]->",
                formatted_value
            )
        
        # add help usage note
        console.print()
        console.print(f"[dim]Use [/][loom.accent2]loom config --help[/][dim] to see available commands[/]")

# * get a specific setting value & print as JSON
@config_app.command()
def get(key: str) -> None:
    if key not in _known_keys():
        raise typer.BadParameter(f"Unknown setting: {key}")
    value = settings_manager.get(key)
    # print JSON for consistency (strings quoted)
    console.print(f"[loom.accent2]{json.dumps(value)}[/]")

# * set a specific setting value; values are JSON-coerced when possible
@config_app.command(name="set")
def set_cmd(key: str, value: str) -> None:
    if key not in _known_keys():
        raise typer.BadParameter(f"Unknown setting: {key}")
    
    # special validation for theme setting
    if key == "theme" and value not in _valid_themes():
        valid_themes = ", ".join(sorted(_valid_themes()))
        raise typer.BadParameter(f"Invalid theme '{value}'. Valid themes: {valid_themes}")
    
    coerced = _coerce_value(value)
    try:
        settings_manager.set(key, coerced)
        
        # refresh console theme if theme was changed
        if key == "theme":
            from ...loom_io.console import refresh_theme
            refresh_theme()
            
    except Exception as e:
        raise typer.BadParameter(str(e))
    console.print(styled_checkmark(), success_gradient(f"Set {key}"), "→", f"[loom.accent2]{json.dumps(coerced)}[/]")

# * reset all settings to defaults
@config_app.command()
def reset() -> None:
    settings_manager.reset()
    console.print(styled_checkmark(), success_gradient("Reset settings to defaults"))

# * show the configuration file path
@config_app.command()
def path() -> None:
    console.print(f"[loom.accent2]{settings_manager.config_path}[/]")

# * interactive theme selector w/ live preview
@config_app.command()
def themes() -> None:
    # run interactive selector
    selected_theme = interactive_theme_selector()
    
    if selected_theme:
        # save the new theme
        settings_manager.set("theme", selected_theme)
        from ...loom_io.console import refresh_theme
        refresh_theme()
        
        console.print(f"\n{styled_checkmark()} {success_gradient(f'Theme set to')} [loom.accent2]{selected_theme}[/]")
        
        # show banner w/ new theme
        console.print("\n[loom.accent]New theme preview:[/]")
        show_loom_art()
    else:
        console.print("\n[dim]Theme selection cancelled[/]")
