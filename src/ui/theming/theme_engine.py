# src/ui/theming/theme_engine.py
# Theme engine: gradient color utilities & logic for consistent CLI styling

from __future__ import annotations

from typing import Any

from ..core.rich_components import Theme, Text
from .theme_definitions import THEMES

# lazy import to avoid circular dependency
_settings_manager: Any = None
_import_attempted = False


def _get_settings_manager() -> Any:
    global _settings_manager, _import_attempted
    if not _import_attempted:
        _import_attempted = True
        try:
            from ...config.settings import settings_manager

            _settings_manager = settings_manager
        except ImportError:
            _settings_manager = None
    return _settings_manager


def _get_theme_colors() -> list[str]:
    # internal: get raw theme color list; use LoomColors for external access
    settings_manager = _get_settings_manager()
    if settings_manager:
        settings = settings_manager.load()
        theme_name = getattr(settings, "theme", "deep_blue")
        return THEMES.get(theme_name, THEMES["deep_blue"])
    return THEMES["deep_blue"]


# * Public alias for backward compatibility (prefer LoomColors for new code)
def get_active_theme() -> list[str]:
    return _get_theme_colors()


# * get current theme name for cache invalidation
def _get_current_theme_name() -> str:
    sm = _get_settings_manager()
    if sm:
        settings = sm.load()
        return getattr(settings, "theme", "deep_blue")
    return "deep_blue"


# descriptor that lazily fetches color from active theme; caches color value & invalidates when theme changes; used by LoomColors to defer color evaluation until first access
class _LazyColorDescriptor:
    def __init__(self, index: int) -> None:
        self._index = index
        self._cached_theme: str | None = None
        self._cached_value: str | None = None

    def __get__(self, obj: object, objtype: type | None = None) -> str:
        current = _get_current_theme_name()
        if self._cached_theme != current:
            self._cached_value = _get_theme_colors()[self._index]
            self._cached_theme = current
        return self._cached_value  # type: ignore[return-value]

    def reset(self) -> None:
        self._cached_theme = None
        self._cached_value = None


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


# * LoomColors provides color constants w/ lazy-loaded theme-aware colors.
# * Dynamic colors (ACCENT_*, ARROW) are deferred until first access & cache-invalidate on theme change.
# * Static colors (SUCCESS_*, WARNING, etc.) are plain class attributes.
class LoomColors:
    # theme-aware accent colors (lazy-loaded, cache-invalidated on theme change)
    ACCENT_PRIMARY = _LazyColorDescriptor(0)
    ACCENT_LIGHT = _LazyColorDescriptor(1)
    ACCENT_SECONDARY = _LazyColorDescriptor(2)
    ACCENT_MEDIUM = _LazyColorDescriptor(3)
    ACCENT_DEEP = _LazyColorDescriptor(4)
    ARROW = _LazyColorDescriptor(2)

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

    @classmethod
    def gradient(cls) -> list[str]:
        # Accent colors in gradient order (primary to deep).
        return [
            cls.ACCENT_PRIMARY,
            cls.ACCENT_LIGHT,
            cls.ACCENT_SECONDARY,
            cls.ACCENT_MEDIUM,
            cls.ACCENT_DEEP,
        ]


def reset_color_cache() -> None:
    for attr in (
        "ACCENT_PRIMARY",
        "ACCENT_LIGHT",
        "ACCENT_SECONDARY",
        "ACCENT_MEDIUM",
        "ACCENT_DEEP",
        "ARROW",
    ):
        desc = LoomColors.__dict__.get(attr)
        if isinstance(desc, _LazyColorDescriptor):
            desc.reset()


# * create natural gradient text w/ smooth RGB color interpolation
def natural_gradient(text: str, colors: list[str] | None = None) -> Text:
    if colors is None:
        colors = LoomColors.gradient()

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
    return natural_gradient(
        text,
        [
            LoomColors.ACCENT_PRIMARY,
            LoomColors.ACCENT_SECONDARY,
            LoomColors.ACCENT_DEEP,
        ],
    )


# * generate Rich theme configuration w/ current colors
def get_loom_theme() -> Theme:
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
            "loom.accent": LoomColors.ACCENT_PRIMARY,
            "loom.accent2": LoomColors.ACCENT_SECONDARY,
            "loom.accent_deep": LoomColors.ACCENT_DEEP,
            "loom.checkmark": LoomColors.CHECKMARK,
            "loom.arrow": LoomColors.ACCENT_SECONDARY,
            # progress styling (brighter, more legible)
            "progress.description": LoomColors.ACCENT_SECONDARY,
            "progress.elapsed": LoomColors.ACCENT_LIGHT,
            "progress.percentage": LoomColors.ACCENT_PRIMARY,
            "progress.remaining": LoomColors.ACCENT_SECONDARY,
            "progress.path": LoomColors.ACCENT_PRIMARY,
            "progress.timer": LoomColors.ACCENT_LIGHT,
            # help styling
            "help.command": LoomColors.ACCENT_PRIMARY,
            "help.option": LoomColors.ACCENT_SECONDARY,
            "help.switch": LoomColors.ACCENT_DEEP,
            # help section headers & structure
            "help.header": LoomColors.ACCENT_LIGHT,
            "help.usage": LoomColors.ACCENT_PRIMARY,
            "help.commands": LoomColors.ACCENT_SECONDARY,
            "help.options": LoomColors.ACCENT_LIGHT,
            "option": LoomColors.ACCENT_SECONDARY,
            "switch": LoomColors.ACCENT_DEEP,
            "metavar": LoomColors.ACCENT_LIGHT,
            "usage": LoomColors.ACCENT_PRIMARY,
        }
    )


# style helpers for common CLI patterns
def styled_checkmark() -> Text:
    return Text("✓", style=LoomColors.CHECKMARK)


def styled_arrow() -> Text:
    return Text("->", style=LoomColors.ARROW)


def styled_bullet() -> Text:
    return Text("•", style=LoomColors.ACCENT_SECONDARY)
