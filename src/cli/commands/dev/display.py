# src/cli/commands/dev/display.py
# Display command for testing UI components & diff interfaces

from __future__ import annotations

import typer

from ...app import app
from ....core.exceptions import handle_loom_error, require_dev_mode
from ....ui.help.help_data import command_help


# * Display UI components for testing (dev/testing only, not for production)
@command_help(
    name="display", 
    description="Display UI components for testing (dev/testing only)",
    long_description=(
        "Shows various UI components for testing theming and interface design. "
        "This command is intended for development and testing purposes only."
    ),
    examples=[
        "loom display",
    ],
    see_also=[],
)
@app.command(help="Display UI components for testing (dev/testing only)")
@handle_loom_error
@require_dev_mode
def display(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & display custom help
    if help:
        from ..help import show_command_help
        show_command_help("display")
        ctx.exit()
    
    # import & run the display diff interface
    from ....ui.diff_resolution.display_diff import main_display_loop
    main_display_loop()