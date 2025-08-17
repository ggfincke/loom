# src/loom_io/generics.py
# Generic utilities for Loom IO operations

from pathlib import Path
from typing import Any
import json

from ..config.settings import settings_manager

# ensure .loom directory exists at import time
def ensure_parent(path: Path) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)

# write JSON w/ UTF-8 encoding, creating parent dirs as needed
def write_json_safe(obj: dict[str, Any], path: Path) -> None:
  ensure_parent(path)
  path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

# read JSON w/ UTF-8 encoding, return dict
def read_json_safe(path: Path) -> dict[str, Any]:
  from ..core.exceptions import JSONParsingError
  
  text = Path(path).read_text(encoding="utf-8")
  try:
    return json.loads(text)
  except json.JSONDecodeError as e:
    # create a trimmed snippet of the offending JSON for the error message
    lines = text.split('\n')
    # JSONDecodeError uses 1-based line numbers
    line_num = e.lineno - 1
    snippet_start = max(0, line_num - 2)
    snippet_end = min(len(lines), line_num + 3)
    snippet_lines = lines[snippet_start:snippet_end]
    
    # add line numbers and highlight the problematic line
    numbered_lines = []
    for i, line in enumerate(snippet_lines, start=snippet_start + 1):
      marker = ">>> " if i == e.lineno else "    "
      numbered_lines.append(f"{marker}{i:3}: {line}")
    
    snippet = "\n".join(numbered_lines)
    raise JSONParsingError(f"Invalid JSON in {path}:\n{snippet}\nError: {e.msg}")
  except Exception as e:
    raise JSONParsingError(f"Error reading JSON from {path}: {e}")

# exit CLI w/ standardized error handling
def exit_with_error(msg: str, code: int = 1) -> None:
  # local import to avoid hard dependency when utils is used outside CLI
  import typer

  typer.echo(msg, err=True)
  raise typer.Exit(code)