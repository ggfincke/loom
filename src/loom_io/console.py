# src/loom_io/console.py
# Global console instance shared across the entire Loom application

from rich.console import Console

# single console instance used by all modules for consistent output & progress coordination
console = Console()