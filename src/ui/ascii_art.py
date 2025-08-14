# src/ui/ascii_art.py
# Banner/art display utilities for CLI

from __future__ import annotations

from pathlib import Path
from ..loom_io.console import console


# * Display the Loom banner if found in new or legacy location
def show_loom_art() -> None:
    candidates = [
        Path(__file__).parent / "assets" / "banner.txt",
        # legacy location before reorg
        Path(__file__).resolve().parents[2] / "cli" / "banner.txt",
    ]
    banner_path = next((p for p in candidates if p.exists()), None)
    if banner_path:
        banner = banner_path.read_text(encoding="utf-8")
        console.print(banner)
    else:
        console.print(
            "LOOM - Smart, precise resume tailoring in seconds", style="bold cyan"
        )
