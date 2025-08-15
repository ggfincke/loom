# src/ui/colors.py
# Gradient color utilities & theme definitions for consistent CLI styling

from __future__ import annotations

from rich.theme import Theme
from rich.text import Text


# theme definitions w/ gradient color palettes for CLI styling
THEMES = {
    "pink_purple": [
        "#ff69b4",  # hot pink
        "#ff1493",  # deep pink  
        "#da70d6",  # orchid
        "#ba55d3",  # medium orchid
        "#9932cc",  # dark orchid
        "#8a2be2",  # blue violet
    ],
    "blue_teal": [
        "#4a90e2",  # sky blue
        "#357abd",  # medium blue
        "#2563eb",  # royal blue
        "#1d4ed8",  # deep blue
        "#1e40af",  # dark blue
        "#0891b2",  # teal
    ],
    "cyber_aqua": [
        "#00ffff",  # pure cyan (electric)
        "#00ccff",  # bright sky cyan
        "#0099ff",  # electric blue
        "#6600ff",  # electric purple (cyber contrast)
        "#9933ff",  # bright purple
        "#00ff99",  # electric mint/green aqua
    ],
    "sunset_coral": [
        "#FF7F50",  # coral
        "#FF8C69",  # salmon
        "#FFA500",  # orange
        "#FFB347",  # peach
        "#FFD700",  # gold
        "#FFDC00",  # bright gold
    ],
    "teal_lime": [
        "#00CED1",  # dark turquoise
        "#20B2AA",  # light sea green
        "#3CB371",  # medium sea green
        "#66CDAA",  # medium aquamarine
        "#90EE90",  # light green
        "#ADFF2F",  # green yellow/lime
    ],
}

# * load active theme colors from settings
def get_active_theme() -> list[str]:
    try:
        from ..config.settings import settings_manager
        settings = settings_manager.load()
        theme_name = getattr(settings, 'theme', 'blue_teal')
        return THEMES.get(theme_name, THEMES["blue_teal"])
    except ImportError:
        # fallback if settings not available
        return THEMES["blue_teal"]

# active theme (set dynamically)
GRADIENT_COLORS = get_active_theme()

# update global gradient colors w/ current theme
def update_gradient_colors():
    global GRADIENT_COLORS
    GRADIENT_COLORS = get_active_theme()

# semantic color mappings for consistent theming  
class LoomColors:
    @classmethod
    def _refresh_colors(cls):
        # refresh colors from current theme
        colors = get_active_theme()
        cls.ACCENT_PRIMARY = colors[0]
        cls.ACCENT_SECONDARY = colors[2] 
        cls.ACCENT_DEEP = colors[4]
    
    # initial color setup (will be updated dynamically)
    ACCENT_PRIMARY = get_active_theme()[0]
    ACCENT_SECONDARY = get_active_theme()[2]
    ACCENT_DEEP = get_active_theme()[4]
    
    # success gradient (complementary green works with all themes)
    SUCCESS_BRIGHT = "#10b981"  # emerald green
    SUCCESS_MEDIUM = "#059669"  # darker emerald
    SUCCESS_DIM = "#047857"     # deep emerald
    
    # status colors
    WARNING = "#ffaa00"   # amber
    ERROR = "#ff4444"     # red
    INFO = "#4488ff"      # blue
    DIM = "#aaaaaa"       # lighter gray for better readability
    
    # special effects
    CHECKMARK = SUCCESS_BRIGHT
    ARROW = ACCENT_SECONDARY


# * create gradient text by applying colors to each character
def gradient_text(text: str, colors: list[str] | None = None) -> Text:
    if colors is None:
        colors = get_active_theme()
    
    if not text or not colors:
        return Text(text)
    
    result = Text()
    color_count = len(colors)
    
    # apply gradient across characters
    for i, char in enumerate(text):
        color_idx = int((i / max(1, len(text) - 1)) * (color_count - 1))
        color_idx = min(color_idx, color_count - 1)
        result.append(char, style=colors[color_idx])
    
    return result


# create gradient effect for success messages  
def success_gradient(text: str) -> Text:
    return gradient_text(text, [LoomColors.SUCCESS_BRIGHT, LoomColors.SUCCESS_MEDIUM, LoomColors.SUCCESS_DIM])


# create gradient effect for accent text
def accent_gradient(text: str) -> Text:
    colors = get_active_theme()
    return gradient_text(text, [colors[0], colors[2], colors[4]])


# * generate Rich theme configuration w/ current colors
def get_loom_theme() -> Theme:
    colors = get_active_theme()
    return Theme({
        # standard semantic colors
        "success": LoomColors.SUCCESS_BRIGHT,
        "warning": LoomColors.WARNING, 
        "error": LoomColors.ERROR,
        "info": LoomColors.INFO,
        "dim": LoomColors.DIM,
        
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
    })

# default theme (updated dynamically)
LOOM_THEME = get_loom_theme()


# style helpers for common CLI patterns
def styled_checkmark() -> Text:
    return Text("✅", style=LoomColors.CHECKMARK)

def styled_arrow() -> Text:
    return Text("→", style=LoomColors.ARROW)

def styled_bullet() -> Text:
    return Text("•", style=LoomColors.ACCENT_SECONDARY)
