# src/cli/commands/cache.py
# Cache management subcommands for AI response caching (stats/clear/clear-expired)

from __future__ import annotations

import typer

from ...ai.cache import get_response_cache
from ...loom_io.console import console
from ...ui.theming.theme_engine import (
    styled_checkmark,
    success_gradient,
    accent_gradient,
)
from ...ui.theming.styled_helpers import styled_setting_line, styled_success_line
from ..app import app
from ..helpers import handle_help_flag
from ...ui.help.help_data import command_help


# * Sub-app for cache commands; registered on root app
cache_app = typer.Typer(
    rich_markup_mode="rich", help="[loom.accent2]Manage AI response cache[/]"
)
app.add_typer(cache_app, name="cache")


# * Print cache statistics
def _print_cache_stats() -> None:
    cache = get_response_cache()
    stats = cache.stats()

    console.print()
    console.print(accent_gradient("Cache Statistics"))
    console.print()

    # Display each stat w/ styled formatting
    stat_lines = [
        ("enabled", "Yes" if stats["enabled"] else "No"),
        ("cache_dir", stats["cache_dir"]),
        ("ttl_days", str(stats["ttl_days"])),
        ("entries", str(stats["entries"])),
        ("expired_entries", str(stats["expired_entries"])),
        ("size", stats["size_human"]),
        ("hits", str(stats["hits"])),
        ("misses", str(stats["misses"])),
        ("hit_rate", stats["hit_rate"]),
    ]

    for key, value in stat_lines:
        console.print(*styled_setting_line(key, f"[loom.accent2]{value}[/]"))

    console.print()
    console.print(
        "[dim]Use [/][loom.accent2]loom cache --help[/][dim] to see available commands[/]"
    )


@command_help(
    name="cache",
    description="Manage AI response cache",
    long_description=(
        "View cache statistics, clear cached responses, or clean up expired entries. "
        "The cache stores successful AI responses to reduce API costs and improve performance."
    ),
    examples=[
        "loom cache  # Show cache statistics",
        "loom cache stats  # Same as above",
        "loom cache clear  # Clear all cached entries",
        "loom cache clear-expired  # Clear only expired entries",
    ],
    see_also=["config"],
)
@cache_app.callback(invoke_without_command=True)
def cache_callback(
    ctx: typer.Context,
    help: bool = typer.Option(
        False, "--help", "-h", help="Show help message and exit."
    ),
) -> None:
    handle_help_flag(ctx, help, "cache")

    if ctx.invoked_subcommand is None:
        _print_cache_stats()


# * Show cache statistics
@cache_app.command()
def stats() -> None:
    _print_cache_stats()


# * Clear all cached entries
@cache_app.command()
def clear() -> None:
    cache = get_response_cache()
    count = cache.clear()

    if count == 0:
        console.print("[dim]Cache is already empty[/]")
    else:
        console.print(
            styled_checkmark(),
            success_gradient(
                f"Cleared {count} cached entr{'y' if count == 1 else 'ies'}"
            ),
        )


# * Clear only expired entries
@cache_app.command(name="clear-expired")
def clear_expired() -> None:
    cache = get_response_cache()
    count = cache.clear_expired()

    if count == 0:
        console.print("[dim]No expired entries to clear[/]")
    else:
        console.print(
            styled_checkmark(),
            success_gradient(
                f"Cleared {count} expired entr{'y' if count == 1 else 'ies'}"
            ),
        )
