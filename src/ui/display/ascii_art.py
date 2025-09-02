# src/ui/display/ascii_art.py
# banner & art display utilities for CLI

from __future__ import annotations

from pathlib import Path
from ..core.rich_components import Text
from ...loom_io.console import console
from ..theming.theme_engine import get_active_theme, natural_gradient

# * Display the Loom banner w/ smooth gradient styling  
def show_loom_art(theme_colors: list[str] | None = None) -> None:
    console.print()
    candidates = [
        Path(__file__).parent / "banner.txt",
        Path(__file__).parent / "assets" / "banner.txt",
    ]
    banner_path = next((p for p in candidates if p.exists()), None)

    # choose 3-stop gradient from theme for nice blending
    if theme_colors is not None:
        theme = theme_colors
    else:
        theme = get_active_theme()
    
    stops = [c for i, c in enumerate(theme) if i in (0, 2, 4)]
    if len(stops) < 2:
        # fallback if theme is short
        stops = theme[:2]

    if banner_path:
        art = banner_path.read_text(encoding="utf-8").splitlines()
        out = Text()
        for line in art:
            out.append(natural_gradient(line, stops))
            out.append("\n")
        console.print(out)
    else:
        # simple fallback title w/ gradient
        title = "LOOM - Smart, precise resume tailoring in seconds"
        console.print(natural_gradient(title, stops))
