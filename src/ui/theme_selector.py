# src/ui/theme_selector.py
# Interactive theme selector w/ live banner preview & arrow key navigation

from __future__ import annotations

from simple_term_menu import TerminalMenu

from ..config.settings import settings_manager
from ..loom_io.console import console, refresh_theme
from .colors import THEMES
from .ascii_art import show_loom_art

# * Capture banner for preview pane
def _capture_banner(theme_name: str) -> str:
    # render banner w/ theme_name & return ANSI string for preview
    original = settings_manager.get("theme")
    try:
        settings_manager.set("theme", theme_name)
        refresh_theme()
        with console.capture() as cap:
            show_loom_art()
        return cap.get()
    finally:
        settings_manager.set("theme", original)
        refresh_theme()

# * Interactive theme selector w/ live preview
def interactive_theme_selector() -> str | None:
    theme_names = sorted(THEMES.keys())
    saved = settings_manager.get("theme")
    start_idx = theme_names.index(saved) if saved in theme_names else 0

    try:
        menu = TerminalMenu(
            theme_names,
            title="🎨 Select a theme",
            cursor_index=start_idx,
            cycle_cursor=True,
            clear_screen=True,
            preview_command=_capture_banner,
            preview_title="Preview",
            preview_size=0.45,
            status_bar=lambda _: f"Use ↑/↓ or j/k • Enter to select • q/Esc to cancel (current: {saved})",
            quit_keys=("q", "escape", "ctrl-c"),
        )

        idx = menu.show()
        if idx is not None and isinstance(idx, int):
            return theme_names[idx]
        return None
    except (OSError, Exception):
        # fallback for non-TTY environments or terminal issues
        return _fallback_theme_selector(theme_names, saved)

# * Fallback theme selector for non-TTY environments
def _fallback_theme_selector(theme_names: list[str], current_theme: str) -> str | None:
    from rich.prompt import Confirm
    
    console.clear()
    console.print("\n[loom.accent]Theme Selector[/]")
    console.print("[dim]Select by number[/]\n")
    
    # display numbered theme list
    console.print("[loom.accent2]Available themes:[/]")
    for i, theme_name in enumerate(theme_names):
        marker = "●" if theme_name == current_theme else "○"
        console.print(f"  {i+1:2d}. {marker} [loom.accent2]{theme_name}[/]")
    
    try:
        console.print()
        choice = console.input(f"[loom.accent]Enter theme number (1-{len(theme_names)}) or 'q' to quit: [/]")
        
        if choice.lower() in ['q', 'quit', 'exit', '']:
            return None
            
        try:
            index = int(choice) - 1
            if 0 <= index < len(theme_names):
                selected_theme = theme_names[index]
                
                # display preview
                console.print(f"\n[loom.accent]Preview of '{selected_theme}' theme:[/]")
                original = settings_manager.get("theme")
                settings_manager.set("theme", selected_theme)
                refresh_theme()
                show_loom_art()
                settings_manager.set("theme", original)
                refresh_theme()
                
                # confirm user selection
                if Confirm.ask(f"\nSet theme to '{selected_theme}'?", default=True):
                    return selected_theme
                return None
            else:
                console.print(f"[error]Invalid choice. Enter number between 1 & {len(theme_names)}[/]")
                return None
        except ValueError:
            console.print("[error]Invalid input. Enter number or 'q' to quit[/]")
            return None
            
    except (EOFError, KeyboardInterrupt):
        console.print("\n[dim]Selection cancelled[/]")
        return None

