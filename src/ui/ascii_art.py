# src/ui/ascii_art.py
# Banner/art display utilities for CLI

from __future__ import annotations

from pathlib import Path
from ..loom_io.console import console


# * Display the Loom banner w/ smooth gradient styling
def show_loom_art() -> None:
    console.print()
    candidates = [
        Path(__file__).parent / "banner.txt",
        Path(__file__).parent / "assets" / "banner.txt",
    ]
    banner_path = next((p for p in candidates if p.exists()), None)
    if banner_path:
        banner = banner_path.read_text(encoding="utf-8")
        # apply smooth gradient to each line
        lines = banner.strip().split('\n')
        
        # use centralized gradient colors for consistency
        from .colors import GRADIENT_COLORS
        gradient_colors = GRADIENT_COLORS
        
        for i, line in enumerate(lines):
            if line.strip():
                # calculate color index based on line position
                color_idx = min(i, len(gradient_colors) - 1)
                color = gradient_colors[color_idx]
                console.print(line, style=color)
            else:
                console.print(line)  # empty line without styling
    else:
        from .colors import accent_gradient
        console.print(accent_gradient("LOOM - Smart, precise resume tailoring in seconds"))
