# src/ui/core/rich_components.py
# Centralized Rich component imports & configuration

from __future__ import annotations

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
]
