# src/cli/commands/config.py
# Settings mgmt subcommands for Loom CLI (list/get/set/reset/path) w/ JSON-backed storage

from __future__ import annotations

import json
from dataclasses import fields
import typer

from ...config.settings import settings_manager, LoomSettings
from ...loom_io.console import console
from ..app import app

# * Sub-app for config commands; registered on root app
config_app = typer.Typer(help="Manage Loom settings stored in ~/.loom/config.json")
app.add_typer(config_app, name="config")

# concise set of known keys for validation
def _known_keys() -> set[str]:
    return {f.name for f in fields(LoomSettings)}

# coerce string value to JSON value (numbers, bools, null) or keep raw string
def _coerce_value(raw: str):
    try:
        # parse JSON for numbers/bools/null/arrays/objects
        return json.loads(raw)
    except Exception:
        return raw

# * list all current settings as JSON
@config_app.command("list")
def list_settings() -> None:
    data = settings_manager.list_settings()
    console.print(json.dumps(data, indent=2))

# * get a specific setting value & print as JSON
@config_app.command()
def get(key: str) -> None:
    if key not in _known_keys():
        raise typer.BadParameter(f"Unknown setting: {key}")
    value = settings_manager.get(key)
    # print JSON for consistency (strings quoted)
    console.print(json.dumps(value))

# * set a specific setting value; values are JSON-coerced when possible
@config_app.command(name="set")
def set_cmd(key: str, value: str) -> None:
    if key not in _known_keys():
        raise typer.BadParameter(f"Unknown setting: {key}")
    coerced = _coerce_value(value)
    try:
        settings_manager.set(key, coerced)
    except Exception as e:
        raise typer.BadParameter(str(e))
    console.print(f"✅ Set {key} -> {json.dumps(coerced)}", style="green")

# * reset all settings to defaults
@config_app.command()
def reset() -> None:
    settings_manager.reset()
    console.print("✅ Reset settings to defaults", style="green")

# * show the configuration file path
@config_app.command()
def path() -> None:
    console.print(str(settings_manager.config_path))
