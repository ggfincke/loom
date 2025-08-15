# src/cli/app.py
# Root Typer application and command registration

from __future__ import annotations

from pathlib import Path
import typer

# patch Typer's Rich help styles before creating the app
from . import typer_styles  # noqa: F401

from ..config.settings import settings_manager
from ..loom_io.console import console
from ..ui.ascii_art import show_loom_art
from ..ui.colors import LoomColors


app = typer.Typer(rich_markup_mode="rich")

# * Load settings & show banner + help when no subcommand is used
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    ctx.obj = settings_manager.load()

    if ctx.invoked_subcommand is None:
        show_loom_art()
        console.print(ctx.get_help())
        ctx.exit()


# ! import command modules here to avoid circular import - they need the 'app' object defined above
from .commands import sectionize as _sectionize  # noqa: F401
from .commands import generate as _generate  # noqa: F401
from .commands import apply as _apply  # noqa: F401
from .commands import tailor as _tailor  # noqa: F401
from .commands import plan as _plan  # noqa: F401
from .commands import config as _config  # noqa: F401
