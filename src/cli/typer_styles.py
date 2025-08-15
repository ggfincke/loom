# src/cli/typer_styles.py
# Patch Typer's Rich help styles globally for CLI styling
from __future__ import annotations

import typer.rich_utils as ru

# width & color system for Rich output
ru.MAX_WIDTH = 100
ru.COLOR_SYSTEM = "auto"

# headings & usage line styling
ru.STYLE_HEADING = "bold bright_white"
ru.STYLE_USAGE = "bold yellow"

# options & commands panel titles
ru.OPTIONS_PANEL_TITLE = "Options"
ru.COMMANDS_PANEL_TITLE = "Commands"

# panel border styling
ru.STYLE_OPTIONS_PANEL_BORDER = "dim"
ru.STYLE_COMMANDS_PANEL_BORDER = "dim"

# option, switch & metavar styles
ru.STYLE_OPTION = "bold bright_cyan"
ru.STYLE_SWITCH = "bright_cyan"
ru.STYLE_NEGATIVE_OPTION = "bold magenta"
ru.STYLE_METAVAR = "bold white"

# command name styling varies by Typer version, set both safely
if hasattr(ru, "STYLE_COMMAND"):
    ru.STYLE_COMMAND = "bold bright_yellow"
if hasattr(ru, "STYLE_COMMANDS"):
    ru.STYLE_COMMANDS = "bold bright_yellow"

# table header & row styling if available
if hasattr(ru, "STYLE_COMMANDS_TABLE_COLUMN_HEADERS"):
    ru.STYLE_COMMANDS_TABLE_COLUMN_HEADERS = "bold bright_black"
if hasattr(ru, "STYLE_COMMANDS_TABLE_ROW"):
    ru.STYLE_COMMANDS_TABLE_ROW = "white"

