# src/loom_io/console.py
# Centralized console management for the entire Loom application

# This module provides a single Console instance that all other modules import to ensure consistent output formatting, theming, & progress coordination.
#
# Usage patterns:
# - For modules w/ UI instance: Use `ui.print()` for progress-aware output
# - For modules without UI: Use `console.print()` directly
# - Tests: Mock only `src.loom_io.console.console` to intercept all output

from __future__ import annotations
from typing import Optional
from rich.console import Console

# single console instance used by all modules for consistent output & progress coordination
console = Console()

# * Get the global console instance (ensures initialization)
def get_console() -> Console:
    return console


# * Configure console w/ specific settings (useful for tests & CLI modes)
def configure_console(
    width: Optional[int] = None,
    height: Optional[int] = None,
    force_terminal: Optional[bool] = None,
    record: bool = False
) -> Console:
    global console
    kwargs = {}
    if width is not None:
        kwargs["width"] = width
    if height is not None:
        kwargs["height"] = height
    if force_terminal is not None:
        kwargs["force_terminal"] = force_terminal
    if record:
        kwargs["record"] = True
    
    if kwargs:  # only recreate if settings provided
        console = Console(**kwargs)
    return console


# * Reset console to default configuration (useful for tests)
def reset_console() -> Console:
    global console
    console = Console()
    return console


# * Refresh console theme w/ current settings
def refresh_theme():
    # ! import here to avoid circular dependency w/ ui module
    try:
        from ..ui.theming.console_theme import refresh_theme as _refresh_theme
        _refresh_theme()
    except ImportError:
        pass

# ! import here to avoid circular dependency w/ ui module
try:
    from ..ui.theming.console_theme import auto_initialize_theme
    auto_initialize_theme()
except ImportError:
    # theme will be set later when ui module is available
    pass


# export main console instance for direct import
__all__ = ["console", "get_console", "configure_console", "reset_console", "refresh_theme"]
