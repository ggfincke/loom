# src/ui/core/rich_components.py
# Centralized Rich component imports & configuration

from __future__ import annotations

from typing import Any

# Core Rich components
from rich.console import Console, RenderableType, Group
from rich.text import Text
from rich.theme import Theme

# Layout & display components
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.padding import Padding

# Progress & interaction components
from rich.progress import Progress, SpinnerColumn, TextColumn, ProgressColumn
from rich.spinner import Spinner


# * Themed Panel builder - consistent styling across UI
def themed_panel(
    content: Any,
    title: str | None = None,
    theme_colors: list[str] | None = None,
    padding: tuple[int, int] = (0, 1),
    **kwargs,
) -> Panel:
    # create Panel w/ consistent theming
    # lazy import to avoid circular dependency
    from ..theming.theme_engine import LoomColors

    colors = theme_colors or LoomColors.gradient()
    formatted_title = f"[bold]{title}[/]" if title else None
    return Panel(
        content,
        title=formatted_title,
        title_align=kwargs.pop("title_align", "left"),
        border_style=kwargs.pop("border_style", colors[2]),
        padding=padding,
        **kwargs,
    )


# * Themed Table builder - consistent styling across UI
def themed_table(
    theme_colors: list[str] | None = None,
    show_header: bool = False,
    **kwargs,
) -> Table:
    # create Table w/ consistent theming
    # lazy import to avoid circular dependency
    from ..theming.theme_engine import LoomColors

    colors = theme_colors or LoomColors.gradient()
    return Table(
        border_style=kwargs.pop("border_style", colors[2]),
        show_header=show_header,
        padding=kwargs.pop("padding", (0, 1, 0, 0)),
        box=kwargs.pop("box", None),
        **kwargs,
    )


__all__ = [
    # Core
    "Console",
    "RenderableType",
    "Group",
    "Text",
    "Theme",
    # Layout & display
    "Panel",
    "Table",
    "Layout",
    "Live",
    "Align",
    "Columns",
    "Padding",
    # Progress & interaction
    "Progress",
    "SpinnerColumn",
    "TextColumn",
    "ProgressColumn",
    "Spinner",
    # Themed builders
    "themed_panel",
    "themed_table",
]
