# src/ui/quick/quick_usage.py
# Quick usage blurb for when no subcommand is provided

from __future__ import annotations

from ...loom_io.console import console
from ..display.ascii_art import show_loom_art


# * Show quick usage details w/ banner, common commands & help references
def show_quick_usage() -> None:
    console.print()
    show_loom_art()
    console.print()

    # quick usage examples
    console.print("[bold white]Quick usage:[/]")

    # commands & descriptions
    commands = [
        ("tailor", "End-to-end tailoring"),
        ("config themes", "Choose visual theme"),
        ("help <command>", "Command-specific help"),
    ]

    # max command length for alignment
    max_cmd_len = max(len(cmd) for cmd, _ in commands)

    for cmd, desc in commands:
        padding = max_cmd_len - len(cmd) + 8
        if "<" in cmd:
            formatted_arg = cmd.replace("help ", "").replace(
                "<command>", "[dim]<command>[/]"
            )
            console.print(
                f"  [dim]loom[/] [bold]help[/] {formatted_arg}{' ' * (padding)}[dim]# {desc}[/]"
            )
        else:
            console.print(
                f"  [dim]loom[/] [bold]{cmd}[/]{' ' * padding}[dim]# {desc}[/]"
            )
    console.print()

    # help reference
    console.print("[dim]For full help:[/] [bold]loom --help[/]")
    console.print()
