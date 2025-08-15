# src/ui/ascii_art.py
# banner & art display utilities for CLI

from __future__ import annotations

from pathlib import Path
from rich.text import Text
from ..loom_io.console import console
from .colors import get_active_theme


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


# * build gradient text by applying colors per character
def gradient_line(line: str, stops: list[str] | None = None) -> Text:
    if stops is None:
        theme = get_active_theme()
        stops = [c for i, c in enumerate(theme) if i in (0, 2, 4)]
        if len(stops) < 2:
            stops = theme[:2]
    
    if not line:
        return Text("")
    n = len(line)
    if n == 1:
        return Text(line, style=stops[0])
    n_stops = len(stops)
    out = Text()
    for i, ch in enumerate(line):
        pos = i / (n - 1)
        seg_pos = pos * (n_stops - 1)
        idx = int(seg_pos)
        if idx >= n_stops - 1:
            color = stops[-1]
        else:
            t = seg_pos - idx
            color = _lerp_color(stops[idx], stops[idx + 1], t)
        out.append(ch, style=color)
    return out

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
            out.append(gradient_line(line, stops))
            out.append("\n")
        console.print(out)
    else:
        # simple fallback title w/ gradient
        title = "LOOM - Smart, precise resume tailoring in seconds"
        console.print(gradient_line(title, stops))
