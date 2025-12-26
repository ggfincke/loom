# src/cli/helpers.py
# Shared CLI helpers for validation, progress, I/O orchestration, & reporting

from __future__ import annotations

import os
from typing import Iterable

import typer


# * handle help flag detection & show custom help if set
def handle_help_flag(ctx: typer.Context, help: bool, command_name: str) -> None:
    if help:
        from .commands.help import show_command_help

        # try to get command object from context for introspection
        command = _get_command_from_context(ctx, command_name)
        show_command_help(command_name, command)
        ctx.exit()


# try to extract command object from Typer context for introspection
def _get_command_from_context(ctx: typer.Context, command_name: str):
    # try to get from parent app's commands dict
    if ctx and hasattr(ctx, "parent") and ctx.parent:
        parent = ctx.parent
        if hasattr(parent, "command"):
            app = parent.command
            # Click apps have a commands dict
            if hasattr(app, "commands") and command_name in app.commands:
                return app.commands[command_name]

    # if we're directly on the command context
    if ctx and hasattr(ctx, "command"):
        return ctx.command

    return None


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
