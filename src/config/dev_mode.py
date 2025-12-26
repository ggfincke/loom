# src/config/dev_mode.py
# Unified dev mode detection with ctx-first, global-fallback pattern
#
# * Placed in config/ (not core/) because it reads settings from disk.
# * Follows "core is pure (no I/O)" rule per docs/contributing.md.

from typing import Optional

import typer

# Cached global dev mode status (only caches the global path, not ctx-based lookups)
_cached_dev_mode: Optional[bool] = None


# * Single source of truth for dev mode status
def is_dev_mode_enabled(ctx: Optional[typer.Context] = None) -> bool:
    """Check if dev mode is enabled.

    Args:
        ctx: Optional Typer context. If provided, uses get_settings(ctx) for
             test injection support. If None, falls back to cached global read.

    Returns:
        True if dev_mode is enabled, False otherwise.
    """
    global _cached_dev_mode

    # ctx-first: respect injected settings for testing
    if ctx is not None:
        from .settings import get_settings

        settings = get_settings(ctx)
        return settings.dev_mode

    # global fallback with caching
    if _cached_dev_mode is None:
        from .settings import settings_manager

        try:
            settings = settings_manager.load()
            _cached_dev_mode = settings.dev_mode
        except (ImportError, AttributeError):
            _cached_dev_mode = False

    return _cached_dev_mode


# * Reset cached dev mode status (called when settings change)
def reset_dev_mode_cache() -> None:
    """Reset cached dev mode status.

    Should be called when settings are modified to ensure fresh reads.
    """
    global _cached_dev_mode
    _cached_dev_mode = None
