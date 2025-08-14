# src/ui/colors.py
# Gradient color utilities & theme definitions for consistent CLI styling

from __future__ import annotations

from rich.theme import Theme
from rich.text import Text


# * Core gradient color palette (pink to purple progression)
GRADIENT_COLORS = [
    "#ff69b4",  # hot pink
    "#ff1493",  # deep pink  
    "#da70d6",  # orchid
    "#ba55d3",  # medium orchid
    "#9932cc",  # dark orchid
    "#8a2be2",  # blue violet
]

# * Semantic color mappings for consistent theming
class LoomColors:
    # primary gradient colors
    ACCENT_PRIMARY = GRADIENT_COLORS[0]      # hot pink
    ACCENT_SECONDARY = GRADIENT_COLORS[2]    # orchid  
    ACCENT_DEEP = GRADIENT_COLORS[4]         # dark orchid
    
    # success gradient (green with pink undertones)
    SUCCESS_BRIGHT = "#00ff88"  # bright green
    SUCCESS_MEDIUM = "#00cc66"  # medium green
    SUCCESS_DIM = "#009944"     # dim green
    
    # status colors
    WARNING = "#ffaa00"   # amber
    ERROR = "#ff4444"     # red
    INFO = "#4488ff"      # blue
    DIM = "#888888"       # gray
    
    # special effects
    CHECKMARK = SUCCESS_BRIGHT
    ARROW = ACCENT_SECONDARY


# * Create gradient text by applying colors to each character/word
def gradient_text(text: str, colors: list[str] | None = None) -> Text:
    if colors is None:
        colors = GRADIENT_COLORS
    
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


# * Create gradient effect for success messages  
def success_gradient(text: str) -> Text:
    return gradient_text(text, [LoomColors.SUCCESS_BRIGHT, LoomColors.SUCCESS_MEDIUM, LoomColors.SUCCESS_DIM])


# * Create gradient effect for accent text
def accent_gradient(text: str) -> Text:
    return gradient_text(text, [LoomColors.ACCENT_PRIMARY, LoomColors.ACCENT_SECONDARY, LoomColors.ACCENT_DEEP])


# * Rich theme configuration w/ Loom gradient colors
LOOM_THEME = Theme({
    # standard semantic colors
    "success": LoomColors.SUCCESS_BRIGHT,
    "warning": LoomColors.WARNING, 
    "error": LoomColors.ERROR,
    "info": LoomColors.INFO,
    "dim": LoomColors.DIM,
    
    # loom-specific colors
    "loom.accent": LoomColors.ACCENT_PRIMARY,
    "loom.accent2": LoomColors.ACCENT_SECONDARY,
    "loom.accent_deep": LoomColors.ACCENT_DEEP,
    "loom.checkmark": LoomColors.CHECKMARK,
    "loom.arrow": LoomColors.ARROW,
    
    # progress styling
    "progress.description": LoomColors.ACCENT_SECONDARY,
    "progress.elapsed": LoomColors.DIM,
    "progress.percentage": LoomColors.ACCENT_PRIMARY,
    "progress.remaining": LoomColors.DIM,
    
    # help styling  
    "help.command": LoomColors.ACCENT_PRIMARY,
    "help.option": LoomColors.ACCENT_SECONDARY,
    "help.switch": LoomColors.ACCENT_DEEP,
})


# * Style helpers for common CLI patterns
def styled_checkmark() -> Text:
    return Text("✅", style=LoomColors.CHECKMARK)

def styled_arrow() -> Text:
    return Text("→", style=LoomColors.ARROW)

def styled_bullet() -> Text:
    return Text("•", style=LoomColors.ACCENT_SECONDARY)