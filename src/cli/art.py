# src/cli/art.py
# CLI art and banner display functionality

from pathlib import Path
from ..loom_io.console import console


# display the loom banner art 
def show_loom_art():
    banner_path = Path(__file__).parent / "banner.txt"
    if banner_path.exists():
        # read as-is so ANSI codes are preserved
        banner = banner_path.read_text(encoding="utf-8")
        console.print(banner)
    else:
        # fallback message if banner file is missing
        console.print("LOOM - Smart, precise resume tailoring in seconds", style="bold cyan")