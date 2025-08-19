from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.console import RenderableType
from readchar import readkey, key
from ...loom_io.console import console

options = ["Staged changes", "Unstaged changes", "Untracked files", "Exit"]
selected = 0

MIN_W, MAX_W = 60, 120
MIN_H, MAX_H = 25, 50

def clamp(n, lo, hi): 
    return max(lo, min(hi, n))

# compute once
FIXED_W = clamp(console.size.width  // 2, MIN_W, MAX_W)
FIXED_H = clamp(console.size.height // 2, MIN_H, MAX_H)

# pretend these are the right-side diffs for each option
diffs_by_opt = {
    "Staged changes": [
        Text("+++ src/app.py: add handler()", style="green"),
        Text("--- src/old.py: remove legacy()", style="red"),
    ],
    "Unstaged changes": [
        Text("+++ README.md: update usage", style="green"),
    ],
    "Untracked files": [
        Text("??? notes/todo.txt (new file)", style="loom.accent"),
    ],
    "Exit": [Text("Press Enter to exit…", style="dim")],
}

def render_screen() -> RenderableType:
    layout = Layout()
    layout.split_row(Layout(name="menu", ratio=1), Layout(name="body", ratio=3))

    # Left menu (highlight the selected row)
    lines = []
    for i, opt in enumerate(options):
        is_sel = i == selected
        prefix = "➤ " if is_sel else "  "
        style  = "reverse bold loom.accent" if is_sel else "loom.accent2"
        lines.append(Text(prefix + opt, style=style))
    menu_panel = Panel(Text("\n").join(lines), title="Options", border_style="loom.accent2")

    # Right diff pane
    current = options[selected]
    body_panel = Panel(Text("\n").join(diffs_by_opt[current]), title=current, border_style="loom.accent2")

    layout["menu"].update(menu_panel)
    layout["body"].update(body_panel)

    target_w = max(60, console.size.width // 2)
    outer = Panel(layout, border_style="loom.accent", width=FIXED_W, height=FIXED_H)
    return Align.left(outer,  vertical="top")

# main display loop
def main_display_loop():
    global selected
    with Live(render_screen(), console=console, screen=True, refresh_per_second=30) as live:
        VALID_KEYS = {key.UP, key.DOWN, "k", "j", key.ENTER, key.ESC, key.CTRL_C}
        while True:
            k = readkey()

            # ignore mouse scroll / other junk
            if k not in VALID_KEYS:
                continue

            if k in (key.UP, "k"):
                selected = (selected - 1) % len(options)
                live.update(render_screen())
            elif k in (key.DOWN, "j"):
                selected = (selected + 1) % len(options)
                live.update(render_screen())
            elif k == key.ENTER:
                break
            elif k in (key.ESC, key.CTRL_C):
                raise SystemExit

    console.print(f"You chose: [bold loom.accent]{options[selected]}[/bold loom.accent]")


# when run directly, execute the main loop
if __name__ == "__main__":
    main_display_loop()
