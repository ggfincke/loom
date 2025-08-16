# src/cli/helpers.py
# Shared CLI helpers for validation, progress, I/O orchestration, and reporting

from __future__ import annotations

from typing import Iterable

import typer


# * validate required CLI arguments & raise typer.BadParameter if missing
def validate_required_args(**kwargs) -> None:
    for _, (value, description) in kwargs.items():
        if not value:
            raise typer.BadParameter(
                f"{description} is required (provide argument or set in config)"
            )



