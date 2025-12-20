# src/ui/theming/theme_engine.py
# Theme engine: gradient color utilities & logic for consistent CLI styling

from __future__ import annotations

from ..core.rich_components import Theme, Text
from .theme_definitions import THEMES

# lazy import to avoid circular dependency
_settings_manager = None


def _get_settings_manager():
    global _settings_manager
    if _settings_manager is None:
        try:
            from ...config.settings import settings_manager

            _settings_manager = settings_manager
        except ImportError:
            _settings_manager = False  # mark as failed to avoid retrying
    return _settings_manager if _settings_manager is not False else None


# * load active theme colors from settings
def get_active_theme() -> list[str]:
    settings_manager = _get_settings_manager()
    if settings_manager:
        settings = settings_manager.load()
        theme_name = getattr(settings, "theme", "deep_blue")
        return THEMES.get(theme_name, THEMES["deep_blue"])
    else:
        # fallback if settings not available
        return THEMES["deep_blue"]


# * RGB color interpolation helper functions for natural gradients
def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(a_hex: str, b_hex: str, t: float) -> str:
    ar, ag, ab = _hex_to_rgb(a_hex)
    br, bg, bb = _hex_to_rgb(b_hex)
    cr = int(round(_lerp(ar, br, t)))
    cg = int(round(_lerp(ag, bg, t)))
    cb = int(round(_lerp(ab, bb, t)))
    return _rgb_to_hex((cr, cg, cb))


# semantic color mappings for consistent theming
class LoomColors:
    # theme-aware accent colors (loaded once at import)
    _colors = get_active_theme()
    ACCENT_PRIMARY = _colors[0]
    ACCENT_SECONDARY = _colors[2]
    ACCENT_DEEP = _colors[4]
    ARROW = _colors[2]

    # success gradient (complementary green works w/ all themes)
    SUCCESS_BRIGHT = "#10b981"  # emerald green
    SUCCESS_MEDIUM = "#059669"  # darker emerald
    SUCCESS_DIM = "#047857"  # deep emerald

    # status colors
    WARNING = "#ffaa00"  # amber
    ERROR = "#ff4444"  # red
    INFO = "#4488ff"  # blue
    DIM = "#aaaaaa"  # lighter gray for better readability
    DEBUG = "#00b5b5"  # dim cyan - consistent for all debug output

    # special effects
    CHECKMARK = SUCCESS_BRIGHT
    ARROW = ACCENT_SECONDARY


# * create natural gradient text w/ smooth RGB color interpolation
def natural_gradient(text: str, colors: list[str] | None = None) -> Text:
    if colors is None:
        colors = get_active_theme()

    if not text or not colors:
        return Text(text)

    if len(colors) < 2:
        return Text(text, style=colors[0] if colors else "white")

    result = Text()
    n = len(text)
    n_stops = len(colors)

    for i, char in enumerate(text):
        if n == 1:
            result.append(char, style=colors[0])
            continue

        # position along the text (0.0 to 1.0)
        pos = i / (n - 1)

        # map position to gradient segments
        seg_pos = pos * (n_stops - 1)
        idx = int(seg_pos)

        if idx >= n_stops - 1:
            color = colors[-1]
        else:
            # interpolation factor between current & next color
            t = seg_pos - idx
            color = _lerp_color(colors[idx], colors[idx + 1], t)

        result.append(char, style=color)

    return result


# create gradient effect for success messages
def success_gradient(text: str) -> Text:
    return natural_gradient(
        text,
        [LoomColors.SUCCESS_BRIGHT, LoomColors.SUCCESS_MEDIUM, LoomColors.SUCCESS_DIM],
    )


# create gradient effect for accent text
def accent_gradient(text: str) -> Text:
    colors = get_active_theme()
    return natural_gradient(text, [colors[0], colors[2], colors[4]])


# * generate Rich theme configuration w/ current colors
def get_loom_theme() -> Theme:
    colors = get_active_theme()
    return Theme(
        {
            # standard semantic colors
            "success": LoomColors.SUCCESS_BRIGHT,
            "warning": LoomColors.WARNING,
            "error": LoomColors.ERROR,
            "info": LoomColors.INFO,
            "dim": LoomColors.DIM,
            "debug": LoomColors.DEBUG,
            # loom-specific colors (dynamic)
            "loom.accent": colors[0],
            "loom.accent2": colors[2],
            "loom.accent_deep": colors[4],
            "loom.checkmark": LoomColors.CHECKMARK,
            "loom.arrow": colors[2],
            # progress styling (brighter, more legible)
            "progress.description": colors[2],
            "progress.elapsed": colors[1],
            "progress.percentage": colors[0],
            "progress.remaining": colors[2],
            "progress.path": colors[0],
            "progress.timer": colors[1],
            # help styling
            "help.command": colors[0],
            "help.option": colors[2],
            "help.switch": colors[4],
            # help section headers & structure
            "help.header": colors[1],
            "help.usage": colors[0],
            "help.commands": colors[2],
            "help.options": colors[1],
            "option": colors[2],
            "switch": colors[4],
            "metavar": colors[1],
            "usage": colors[0],
        }
    )


# default theme (updated dynamically)
LOOM_THEME = get_loom_theme()


# style helpers for common CLI patterns
def styled_checkmark() -> Text:
    return Text("✓", style=LoomColors.CHECKMARK)


def styled_arrow() -> Text:
    return Text("->", style=LoomColors.ARROW)


def styled_bullet() -> Text:
    return Text("•", style=LoomColors.ACCENT_SECONDARY)
