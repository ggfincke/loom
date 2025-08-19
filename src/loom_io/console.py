# src/loom_io/console.py
# Global console instance shared across the entire Loom application

from rich.console import Console

# single console instance used by all modules for consistent output & progress coordination
console = Console()

# * Refresh console theme w/ current settings (imported from ui module)
def refresh_theme():
    try:
        from ..ui.theming.console_theme import refresh_theme as _refresh_theme
        _refresh_theme()
    except ImportError:
        pass

# lazy theme initialization moved to ui.console_theme module
try:
    from ..ui.theming.console_theme import auto_initialize_theme
    auto_initialize_theme()
except ImportError:
    # theme will be set later when ui module is available
    pass
