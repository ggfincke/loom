# src/ui/theme_selector.py
# Interactive theme selector w/ live banner preview & arrow key navigation

from __future__ import annotations

from rich.prompt import Confirm

from ..config.settings import settings_manager
from ..loom_io.console import console, refresh_theme
from .colors import THEMES
from .ascii_art import show_loom_art


# * Interactive theme selector w/ live preview
def interactive_theme_selector() -> str | None:
    theme_names = sorted(THEMES.keys())
    current_theme = settings_manager.get("theme")
    
    # simplified keyboard input using rich prompts
    console.clear()
    console.print("\n[loom.accent]Interactive Theme Selector[/]")
    console.print("[dim]Navigate w/ numbers, press Enter to confirm[/]\n")
    
    # show current preview
    current_index = theme_names.index(current_theme) if current_theme in theme_names else 0
    _show_theme_preview(theme_names[current_index])
    
    # show numbered theme list
    console.print("\n[loom.accent2]Available themes:[/]")
    for i, theme_name in enumerate(theme_names):
        marker = "●" if theme_name == current_theme else "○"
        console.print(f"  {i+1:2d}. {marker} [loom.accent2]{theme_name}[/]")
    
    # prompt for selection
    try:
        console.print()
        choice = console.input("[loom.accent]Enter theme number (1-{}) or 'q' to quit: [/]".format(len(theme_names)))
        
        if choice.lower() in ['q', 'quit', 'exit', '']:
            return None
            
        try:
            index = int(choice) - 1
            if 0 <= index < len(theme_names):
                selected_theme = theme_names[index]
                
                # show preview of selected theme
                console.print(f"\n[loom.accent]Preview of '{selected_theme}' theme:[/]")
                _show_theme_preview(selected_theme)
                
                # confirm selection
                if Confirm.ask(f"\nSet theme to '{selected_theme}'?", default=True):
                    return selected_theme
                return None
            else:
                console.print(f"[error]Invalid choice. Please enter a number between 1 & {len(theme_names)}[/]")
                return None
        except ValueError:
            console.print("[error]Invalid input. Please enter a number or 'q' to quit[/]")
            return None
            
    except (EOFError, KeyboardInterrupt):
        console.print("\n[dim]Selection cancelled[/]")
        return None


# show banner preview w/ specified theme
def _show_theme_preview(theme_name: str) -> None:
    # temporarily switch theme for preview
    original_theme = settings_manager.get("theme")
    settings_manager.set("theme", theme_name)
    refresh_theme()
    
    # show banner w/ new theme
    show_loom_art()
    
    # restore original theme
    settings_manager.set("theme", original_theme)
    refresh_theme()

