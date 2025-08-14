# src/ui/ascii_art.py
# Banner/art display utilities for CLI

from __future__ import annotations

from pathlib import Path
from ..loom_io.console import console


# * Display the Loom banner w/ smooth pink/purple gradient styling
def show_loom_art() -> None:
    console.print()
    candidates = [
        Path(__file__).parent / "banner.txt",
        Path(__file__).parent / "assets" / "banner.txt",
    ]
    banner_path = next((p for p in candidates if p.exists()), None)
    if banner_path:
        banner = banner_path.read_text(encoding="utf-8")
        # apply smooth pink/purple gradient to each line
        lines = banner.strip().split('\n')
        
        # gradient colors from bright pink to deep purple
        gradient_colors = [
            "#ff69b4",  # hot pink
            "#ff1493",  # deep pink
            "#da70d6",  # orchid
            "#ba55d3",  # medium orchid
            "#9932cc",  # dark orchid
            "#8a2be2",  # blue violet
        ]
        
        for i, line in enumerate(lines):
            if line.strip():
                # calculate color index based on line position
                color_idx = min(i, len(gradient_colors) - 1)
                color = gradient_colors[color_idx]
                console.print(line, style=color)
            else:
                console.print(line)  # empty line without styling
    else:
        console.print(
            "LOOM - Smart, precise resume tailoring in seconds", style="bold cyan"
        )
