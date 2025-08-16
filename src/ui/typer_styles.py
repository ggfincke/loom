# src/ui/typer_styles.py
# Patch Typer's Rich help styles globally for CLI styling
from __future__ import annotations

import typer.rich_utils as ru

# width & color system for Rich output
ru.MAX_WIDTH = 100  # type: ignore
ru.COLOR_SYSTEM = "auto"  # type: ignore

# headings & usage line styling
ru.STYLE_HEADING = "bold bright_white"  # type: ignore
ru.STYLE_USAGE = "bold yellow"  # type: ignore

# options & commands panel titles
ru.OPTIONS_PANEL_TITLE = "Options"  # type: ignore
ru.COMMANDS_PANEL_TITLE = "Commands"  # type: ignore

# panel border styling
ru.STYLE_OPTIONS_PANEL_BORDER = "dim"  # type: ignore
ru.STYLE_COMMANDS_PANEL_BORDER = "dim"  # type: ignore

# option, switch & metavar styles
ru.STYLE_OPTION = "bold bright_cyan"  # type: ignore
ru.STYLE_SWITCH = "bright_cyan"  # type: ignore
ru.STYLE_NEGATIVE_OPTION = "bold magenta"  # type: ignore
ru.STYLE_METAVAR = "bold white"  # type: ignore

# command name styling varies by Typer version, set both safely
if hasattr(ru, "STYLE_COMMAND"):
    ru.STYLE_COMMAND = "bold bright_yellow"  # type: ignore
if hasattr(ru, "STYLE_COMMANDS"):
    ru.STYLE_COMMANDS = "bold bright_yellow"  # type: ignore

# table header & row styling if available
if hasattr(ru, "STYLE_COMMANDS_TABLE_COLUMN_HEADERS"):
    ru.STYLE_COMMANDS_TABLE_COLUMN_HEADERS = "bold bright_black"  # type: ignore
if hasattr(ru, "STYLE_COMMANDS_TABLE_ROW"):
    ru.STYLE_COMMANDS_TABLE_ROW = "white"  # type: ignore

