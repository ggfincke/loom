# src/cli/commands/dev/display.py
# Display command for testing UI components & diff interfaces w/ dev flag

from __future__ import annotations

import typer

from ....config.settings import get_settings
from ....core.exceptions import handle_loom_error, DevModeError
from ....ui.diff_resolution.display_diff import main_display_loop
from ....ui.help.help_data import command_help
from ...app import app


# * Display UI components for testing (dev/testing only, not for production)
@command_help(
    name="display", 
    description="Display UI components for testing (dev/testing only)",
    long_description=(
        "Shows various UI components for testing theming & interface design. "
        "This command is intended for development & testing purposes only."
    ),
    examples=[
        "loom display",
    ],
    see_also=[],
)
@app.command(help="Display UI components for testing (dev/testing only)")
@handle_loom_error
def display(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & display custom help
    if help:
        from ..help import show_command_help
        show_command_help("display")
        ctx.exit()
    
    # check if dev_mode is globally enabled
    settings = get_settings(ctx)
    if not settings.dev_mode:
        raise DevModeError(
            "Development mode required. Enable with: loom config set dev_mode true"
        )
    
    # run the display diff interface
    main_display_loop()