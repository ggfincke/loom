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
    "deep_blue": [
        "#4a90e2",  # sky blue
        "#357abd",  # medium blue
        "#2563eb",  # royal blue
        "#1d4ed8",  # deep blue
        "#1e40af",  # dark blue
        "#0891b2",  # teal
    ],
    "cyber_neon": [
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
    "volcanic_fire": [
        "#FFD700",  # gold
        "#FFA500",  # orange
        "#FF6347",  # tomato
        "#FF4500",  # orange red
        "#DC143C",  # crimson
        "#8B0000",  # dark red
    ],
    "arctic_ice": [
        "#F0F8FF",  # alice blue
        "#E6F3FF",  # light blue
        "#B0E0E6",  # powder blue
        "#87CEEB",  # sky blue
        "#4682B4",  # steel blue
        "#2F4F4F",  # dark slate gray
    ],
    "synthwave_retro": [
        "#FF00FF",  # magenta
        "#FF0080",  # deep pink
        "#8000FF",  # electric violet
        "#4000FF",  # electric indigo
        "#0080FF",  # electric blue
        "#00FFFF",  # cyan
    ],
    "autumn_harvest": [
        "#FFE4B5",  # moccasin
        "#DEB887",  # burlywood
        "#D2691E",  # chocolate
        "#CD853F",  # peru
        "#A0522D",  # sienna
        "#8B4513",  # saddle brown
    ],
    "galaxy_nebula": [
        "#E6E6FA",  # lavender
        "#DDA0DD",  # plum
        "#DA70D6",  # orchid
        "#9370DB",  # medium purple
        "#6A5ACD",  # slate blue
        "#483D8B",  # dark slate blue
    ],
    "desert_sand": [
        "#FFF8DC",  # cornsilk
        "#F5DEB3",  # wheat
        "#DEB887",  # burlywood
        "#D2B48C",  # tan
        "#BC8F8F",  # rosy brown
        "#A0522D",  # sienna
    ],
    "midnight_purple": [
        "#E6E6FA",  # lavender
        "#C8A2C8",  # lilac
        "#9966CC",  # amethyst
        "#6A0DAD",  # blue violet
        "#4B0082",  # indigo
        "#2E0054",  # dark indigo
    ],
    "ruby_crimson": [
        "#FFB6C1",  # light pink
        "#FF69B4",  # hot pink
        "#FF1493",  # deep pink
        "#DC143C",  # crimson
        "#B22222",  # fire brick
        "#8B0000",  # dark red
    ],
    "emerald_mint": [
        "#98FB98",  # pale green
        "#00FA9A",  # medium spring green
        "#00FF7F",  # spring green
        "#00CED1",  # dark turquoise
        "#20B2AA",  # light sea green
        "#008B8B",  # dark cyan
    ],
    "steel_silver": [
        "#F8F8FF",  # ghost white
        "#E6E6FA",  # lavender
        "#D3D3D3",  # light gray
        "#A9A9A9",  # dark gray
        "#708090",  # slate gray
        "#2F4F4F",  # dark slate gray
    ],
    "copper_bronze": [
        "#FFDAB9",  # peach puff
        "#DEB887",  # burlywood
        "#CD853F",  # peru
        "#B8860B",  # dark goldenrod
        "#A0522D",  # sienna
        "#8B4513",  # saddle brown
    ],
    "lavender_mist": [
        "#F8F8FF",  # ghost white
        "#E6E6FA",  # lavender
        "#DDA0DD",  # plum
        "#BA55D3",  # medium orchid
        "#9370DB",  # medium purple
        "#663399",  # rebecca purple
    ],
}

# * load active theme colors from settings
def get_active_theme() -> list[str]:
    try:
        # ! import here to avoid circular dependency w/ settings
        from ..config.settings import settings_manager
        settings = settings_manager.load()
        theme_name = getattr(settings, 'theme', 'deep_blue')
        return THEMES.get(theme_name, THEMES["deep_blue"])
    except ImportError:
        # fallback if settings not available
        return THEMES["deep_blue"]

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
