# src/ui/theming/console_theme.py
# Console theme initialization & management for Rich styling

from __future__ import annotations

from ...loom_io.console import console


# * initialize gradient theme after theme_engine module is available
def initialize_theme() -> None:
    from .theme_engine import get_loom_theme

    console.push_theme(get_loom_theme())


# * Refresh console theme w/ current settings
def refresh_theme() -> None:
    try:
        from .theme_engine import get_loom_theme
        from rich.theme import ThemeStackError

        # pop existing theme (if any was pushed) & push new one
        try:
            console.pop_theme()
        except ThemeStackError:
            pass  # no theme was pushed yet, that's fine
        console.push_theme(get_loom_theme())
    except ImportError:
        pass


# lazy theme initialization to avoid circular imports
def auto_initialize_theme() -> None:
    try:
        initialize_theme()
    except ImportError:
        # theme will be set later when colors module is available
        pass
