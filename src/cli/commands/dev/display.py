# src/cli/commands/dev/display.py
# Display command for testing UI components & diff interfaces w/ dev flag

from __future__ import annotations

import typer

from ...decorators import handle_loom_error, require_dev_mode
from ....core.constants import EditOperation
from ....ui.diff_resolution.diff_display import main_display_loop
from ....ui.help.help_data import command_help
from ...app import app
from ...helpers import handle_help_flag


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
@require_dev_mode
def display(
    ctx: typer.Context,
    help: bool = typer.Option(
        False, "--help", "-h", help="Show help message and exit."
    ),
) -> None:
    # Detect help flag & display custom help
    handle_help_flag(ctx, help, "display")

    # Create sample edit operations for testing
    sample_operations = [
        EditOperation(
            operation="replace_line",
            line_number=6,
            content="Experienced Python developer w/ 5+ years building scalable web applications & cloud infrastructure.",
            reasoning="Emphasize Python experience & cloud skills to match job requirements",
            confidence=0.92,
        ),
        EditOperation(
            operation="insert_after",
            line_number=11,
            content="• AWS (Lambda, EC2, S3), Docker, Kubernetes",
            reasoning="Add specific cloud technologies mentioned in job posting",
            confidence=0.88,
        ),
        EditOperation(
            operation="replace_range",
            line_number=15,
            start_line=15,
            end_line=16,
            content="• Architected & deployed microservices handling 1M+ requests/day\n• Led cross-functional team of 4 engineers delivering high-impact features",
            reasoning="Quantify impact & leadership experience to strengthen candidacy",
            confidence=0.91,
        ),
        EditOperation(
            operation="delete_range",
            line_number=19,
            start_line=19,
            end_line=19,
            reasoning="Remove outdated technology reference that doesn't align w/ role",
            confidence=0.85,
        ),
        EditOperation(
            operation="replace_line",
            line_number=23,
            content="• Built RESTful APIs using FastAPI & Django serving 500K+ daily users",
            reasoning="Highlight specific Python frameworks and scale metrics",
            confidence=0.89,
        ),
    ]

    # Run the display diff interface w/ sample operations
    main_display_loop(sample_operations)
