# src/ui/console_theme.py
# Console theme initialization & management for Rich styling

from __future__ import annotations

from ..loom_io.console import console


# * initialize gradient theme after colors module is available
def initialize_theme():
    from .colors import get_loom_theme
    console.push_theme(get_loom_theme())


# * Refresh console theme w/ current settings
def refresh_theme():
    try:
        from .colors import get_loom_theme
        # pop existing theme and push new one
        if console._theme_stack:
            console.pop_theme()
        console.push_theme(get_loom_theme())
    except ImportError:
        pass


# lazy theme initialization to avoid circular imports
def auto_initialize_theme():
    try:
        initialize_theme()
    except ImportError:
        # theme will be set later when colors module is available
        pass