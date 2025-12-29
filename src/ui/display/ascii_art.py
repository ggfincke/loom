# src/ui/display/ascii_art.py
# banner & art display utilities for CLI

from __future__ import annotations

from pathlib import Path
from ..core.rich_components import Text
from ...loom_io.console import console
from ..theming.theme_engine import LoomColors, natural_gradient


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
        stops = [c for i, c in enumerate(theme_colors) if i in (0, 2, 4)]
        if len(stops) < 2:
            # fallback if theme is short
            stops = theme_colors[:2]
    else:
        stops = [
            LoomColors.ACCENT_PRIMARY,
            LoomColors.ACCENT_SECONDARY,
            LoomColors.ACCENT_DEEP,
        ]

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
