# src/loom_io/console.py
# Centralized console management for the entire Loom application

# This module provides a single Console instance that all other modules import to ensure consistent output formatting, theming, & progress coordination.
#
# Architecture notes:
# - Console is created as a bare Console() at import time (lightweight, no theme loading)
# - Theme initialization happens explicitly in app.py:main_callback() via auto_initialize_theme()
# - The _ConsoleProxy pattern allows reconfiguring/resetting without breaking module-level references
#
# Usage patterns:
# - For modules w/ UI instance: Use `ui.print()` for progress-aware output
# - For modules without UI: Use `console.print()` directly
# - Tests: Use reset_console() for isolation; mock `src.loom_io.console.console` to intercept output

from __future__ import annotations
from typing import Optional, Any
from rich.console import Console


# proxy delegating to underlying Console instance; allows reconfiguring/resetting console w/out breaking module-level references; all Console methods forwarded via __getattr__
class _ConsoleProxy:
    __slots__ = ("_console",)

    def __init__(self) -> None:
        self._console = Console()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._console, name)

    def _set_console(self, new_console: Console) -> None:
        self._console = new_console

    def _get_console(self) -> Console:
        return self._console


# single proxy instance used by all modules for consistent output & progress coordination
console = _ConsoleProxy()


# * Get the underlying Console instance
def get_console() -> Console:
    # handle both proxy & direct Console (e.g., when patched in tests)
    if hasattr(console, "_get_console"):
        return console._get_console()
    return console  # type: ignore[return-value]


# * Configure console w/ specific settings (useful for tests & CLI modes)
def configure_console(
    width: Optional[int] = None,
    height: Optional[int] = None,
    force_terminal: Optional[bool] = None,
    record: bool = False,
) -> Console:
    kwargs: dict[str, Any] = {}
    if width is not None:
        kwargs["width"] = width
    if height is not None:
        kwargs["height"] = height
    if force_terminal is not None:
        kwargs["force_terminal"] = force_terminal
    if record:
        kwargs["record"] = True

    if kwargs:  # only recreate if settings provided
        console._set_console(Console(**kwargs))
    return console._get_console()


# * Reset console to default configuration (useful for tests)
def reset_console() -> Console:
    console._set_console(Console())
    return console._get_console()


# * Refresh console theme w/ current settings.
# * Theme initialization happens explicitly in app.py:main_callback() via auto_initialize_theme().
# * Call this function after settings changes (e.g., theme selection) to apply new theme.
def refresh_theme() -> None:
    # ! import here to avoid circular dependency w/ ui module
    try:
        from ..ui.theming.console_theme import refresh_theme as _refresh_theme

        _refresh_theme()
    except ImportError:
        pass


# export main console instance for direct import
__all__ = [
    "console",
    "get_console",
    "configure_console",
    "reset_console",
    "refresh_theme",
]
