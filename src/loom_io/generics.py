# src/loom_io/generics.py
# Generic utilities for Loom IO operations

from pathlib import Path
from typing import Any
import json

from ..config.settings import settings_manager

# ensure .loom directory exists at import time
def ensure_parent(path: Path) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)

# write JSON with UTF-8 encoding, creating parent dirs as needed
def write_json_safe(obj: dict[str, Any], path: Path) -> None:
  ensure_parent(path)
  path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

# read JSON w/ UTF-8 encoding, return dict
def read_json_safe(path: Path) -> dict[str, Any]:
  text = Path(path).read_text(encoding="utf-8")
  return json.loads(text)

# standardized CLI exit function
def exit_with_error(msg: str, code: int = 1) -> None:
  # local import to avoid hard dependency when utils is used outside CLI
  import typer

  typer.echo(msg, err=True)
  raise typer.Exit(code)