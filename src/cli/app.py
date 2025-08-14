# src/cli/app.py
# Root Typer application and command registration

from __future__ import annotations

from pathlib import Path
import typer

from ..config.settings import settings_manager
from ..loom_io.console import console
from ..ui.ascii_art import show_loom_art


app = typer.Typer()


# * Load settings & show banner + help when no subcommand is used
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    ctx.obj = settings_manager.load()

    if ctx.invoked_subcommand is None:
        show_loom_art()
        console.print(ctx.get_help())
        ctx.exit()


# Import command modules to attach their @app.command definitions
# This import side-effect registers commands on the global `app` above.
from .commands import sectionize as _sectionize  # noqa: F401
from .commands import generate as _generate  # noqa: F401
from .commands import apply as _apply  # noqa: F401
from .commands import tailor as _tailor  # noqa: F401
from .commands import plan as _plan  # noqa: F401

