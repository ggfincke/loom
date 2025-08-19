# src/ui/theming/__init__.py
# Theming utilities: colors, console theme, Typer styles, selectors

from .colors import (
    THEMES,
    get_active_theme,
    update_gradient_colors,
    LoomColors,
    natural_gradient,
    gradient_text,
    success_gradient,
    accent_gradient,
    get_loom_theme,
    styled_checkmark,
    styled_arrow,
    styled_bullet,
)
from .console_theme import initialize_theme, refresh_theme, auto_initialize_theme
from .theme_selector import interactive_theme_selector
# typer_styles doesn't export functions, it just patches typer

__all__ = [
    "THEMES",
    "get_active_theme",
    "update_gradient_colors", 
    "LoomColors",
    "natural_gradient",
    "gradient_text",
    "success_gradient",
    "accent_gradient",
    "get_loom_theme",
    "styled_checkmark",
    "styled_arrow",
    "styled_bullet",
    "initialize_theme",
    "refresh_theme", 
    "auto_initialize_theme",
    "interactive_theme_selector",
]

