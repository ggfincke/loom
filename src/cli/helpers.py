# src/cli/helpers.py
# Shared CLI helpers for validation, progress, I/O orchestration, & reporting

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from ..core.constants import RiskLevel, ValidationPolicy
    from .runner import TailoringMode

# ---------------------------------------------------------------------------
# SETTINGS ACCESS PATTERNS
# ---------------------------------------------------------------------------
# Standard pattern for commands needing argument resolution:
#   settings = get_settings(ctx)
#   resolver = ArgResolver(settings)
#   resolved = resolver.resolve_common(resume=..., job=..., model=...)
#
# For commands only reading settings:
#   settings = get_settings(ctx)
#   value = settings.field_name
#
# For config management commands only (mutations):
#   settings_manager.get_field("key")
#   settings_manager.set_field("key", value)
# ---------------------------------------------------------------------------


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
    from click import Group

    # try to get from parent app's commands dict
    if ctx and hasattr(ctx, "parent") and ctx.parent:
        parent = ctx.parent
        if hasattr(parent, "command"):
            app = parent.command
            # Click Group apps have a commands dict
            if isinstance(app, Group) and command_name in app.commands:
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


# * Unified command execution for generate/apply/tailor/plan
def run_tailoring_command(
    ctx: typer.Context,
    mode: "TailoringMode",
    *,
    resume: Path | None = None,
    job: Path | None = None,
    model: str | None = None,
    sections_path: Path | None = None,
    edits_json: Path | None = None,
    output_resume: Path | None = None,
    risk: "RiskLevel | None" = None,
    on_error: "ValidationPolicy | None" = None,
    preserve_formatting: bool = True,
    preserve_mode: str = "in_place",
    interactive: bool = True,
    user_prompt: str | None = None,
) -> None:
    # unified command execution for generate/apply/tailor/plan; resolves arguments via settings & ArgResolver, builds TailoringContext, & executes via TailoringRunner
    from .logic import ArgResolver
    from .runner import TailoringRunner, build_tailoring_context
    from ..config.settings import get_settings

    settings = get_settings(ctx)
    resolver = ArgResolver(settings)

    tailoring_ctx = build_tailoring_context(
        settings,
        resolver,
        resume=resume,
        job=job,
        model=model,
        sections_path=sections_path,
        edits_json=edits_json,
        output_resume=output_resume,
        risk=risk,
        on_error=on_error,
        preserve_formatting=preserve_formatting,
        preserve_mode=preserve_mode,
        interactive=interactive,
        user_prompt=user_prompt,
    )

    runner = TailoringRunner(mode, tailoring_ctx)
    runner.run()
