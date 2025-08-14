# src/loom_io/console.py
# Global console instance shared across the entire Loom application

from rich.console import Console

# single console instance used by all modules for consistent output & progress coordination
console = Console()

# * Initialize gradient theme after colors module is available
def _initialize_theme():
    from ..ui.colors import LOOM_THEME
    console.push_theme(LOOM_THEME)

# lazy theme initialization to avoid circular imports
try:
    _initialize_theme()
except ImportError:
    # theme will be set later when colors module is available
    pass