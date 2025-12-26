# src/ui/theming/styled_helpers.py
# Pre-composed styling helpers for common CLI output patterns

from __future__ import annotations

import json
from typing import Any

from .theme_engine import styled_checkmark, styled_arrow, success_gradient, styled_bullet


def styled_success_line(label: str, value: str | None = None) -> list:
    """Pre-composed success line: checkmark + gradient label [+ arrow + value].

    Returns list of renderables for console.print(*result).
    """
    parts: list[Any] = [styled_checkmark(), success_gradient(label)]
    if value is not None:
        parts.extend([styled_arrow(), value])
    return parts


def styled_setting_line(key: str, value: str) -> list:
    """Pre-composed setting display: bullet + key + arrow + value.

    Returns list of renderables for console.print(*result).
    """
    return [
        styled_bullet(),
        f"[bold white]{key}[/]",
        "[loom.accent2]->",
        value,
    ]


def styled_provider_line(provider: str, status_icon: Any, status_text: str) -> list:
    """Pre-composed provider header line for models display.
    
    Returns list of renderables for console.print(*result).
    """
    return [f"[bold white]{provider}[/]", status_icon, status_text]


def format_setting_value(value: Any) -> str:
    """Format a setting value with consistent styling."""
    if isinstance(value, str):
        return f'[loom.accent2]"{value}"[/]'
    elif isinstance(value, bool):
        return f"[loom.accent2]{str(value).lower()}[/]"
    elif isinstance(value, (int, float)):
        return f"[loom.accent2]{value}[/]"
    else:
        return f"[loom.accent2]{json.dumps(value)}[/]"
