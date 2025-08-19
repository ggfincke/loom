# src/cli/helpers.py
# Shared CLI helpers for validation, progress, I/O orchestration, & reporting

from __future__ import annotations

import os
from typing import Iterable

import typer


# * validate required CLI arguments & raise typer.BadParameter if missing
def validate_required_args(**kwargs) -> None:
    for _, (value, description) in kwargs.items():
        if not value:
            raise typer.BadParameter(
                f"{description} is required (provide argument or set in config)"
            )


# * Detect if running in test environment to avoid TTY-dependent features
def is_test_environment() -> bool:
    # check for pytest environment variable
    if "PYTEST_CURRENT_TEST" in os.environ:
        return True
    
    # check for typer test runner indicators
    if os.environ.get("NO_COLOR") == "1" and os.environ.get("TERM") == "dumb":
        return True
    
    # check for other test indicators
    if any(test_var in os.environ for test_var in ["_PYTEST_RAISE", "PYTEST_VERSION"]):
        return True
    
    return False



