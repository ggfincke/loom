# src/cli/app.py
# Root Typer application and command registration

from __future__ import annotations

import typer

# patch Typer's Rich help styles before creating the app
from ..ui import typer_styles  # noqa: F401

from ..config.settings import settings_manager
from ..loom_io.console import console


app = typer.Typer(
    rich_markup_mode="rich", 
    add_completion=False, 
    no_args_is_help=False,
    context_settings={"help_option_names": ["--help", "-h"]}
)

# * Load settings & show quick usage when no subcommand is used
@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    help_raw: bool = typer.Option(False, "--help-raw", help="Show raw Typer help instead of branded help"),
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # respect injected ctx.obj from tests/embedding; only load if absent
    if getattr(ctx, "obj", None) is None:
        ctx.obj = settings_manager.load()
    
    if ctx.invoked_subcommand is None:
        if help_raw:
            # show raw typer help
            console.print(ctx.get_help())
        elif help:
            # show full branded help (import here to avoid circular import)
            from .commands.help import show_main_help
            show_main_help(app)
        else:
            # show quick usage blurb
            from ..ui.quick.quick_usage import show_quick_usage
            show_quick_usage()
        ctx.exit()


# ! import command modules here to avoid circular import (need 'app' object defined above)
from .commands import sectionize as _sectionize  # noqa: F401
from .commands import generate as _generate  # noqa: F401
from .commands import apply as _apply  # noqa: F401
from .commands import tailor as _tailor  # noqa: F401
from .commands import plan as _plan  # noqa: F401
from .commands import config as _config  # noqa: F401
from .commands import models as _models  # noqa: F401
from .commands import help as _help  # noqa: F401
