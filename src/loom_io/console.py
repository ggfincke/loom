# src/loom_io/console.py
# Global console instance shared across the entire Loom application

from rich.console import Console

# single console instance used by all modules for consistent output & progress coordination
console = Console()

# * Initialize gradient theme after colors module is available
def _initialize_theme():
    from ..ui.colors import get_loom_theme
    console.push_theme(get_loom_theme())

# * Refresh console theme with current settings
def refresh_theme():
    try:
        from ..ui.colors import get_loom_theme
        # pop existing theme and push new one
        if console._theme_stack:
            console.pop_theme()
        console.push_theme(get_loom_theme())
    except ImportError:
        pass

# lazy theme initialization to avoid circular imports
try:
    _initialize_theme()
except ImportError:
    # theme will be set later when colors module is available
    pass