# src/core/debug.py
# Debug logging utilities for verbose output & troubleshooting

import os
from typing import Optional

# global debug state
_debug_enabled = False

# * Enable debug mode
def enable_debug() -> None:
    global _debug_enabled
    _debug_enabled = True

# * Disable debug mode
def disable_debug() -> None:
    global _debug_enabled
    _debug_enabled = False

# * Check if debug mode is enabled
def is_debug_enabled() -> bool:
    global _debug_enabled
    return _debug_enabled or os.getenv("LOOM_DEBUG", "").lower() in ("1", "true", "yes")

# * Print debug message if debug mode is enabled
def debug_print(message: str, category: str = "DEBUG") -> None:
    if is_debug_enabled():
        # lazy import to avoid circular dependencies
        from ..loom_io.console import console
        console.print(f"[dim yellow]\\[{category}][/] {message}")

# * Print AI-related debug information
def debug_ai(message: str) -> None:
    debug_print(message, "AI")

# * Print error details in debug mode
def debug_error(error: Exception, context: str = "") -> None:
    if is_debug_enabled():
        error_msg = f"Exception: {type(error).__name__}: {str(error)}"
        if context:
            error_msg = f"{context} - {error_msg}"
        debug_print(error_msg, "ERROR")

# * Debug API request/response details
def debug_api_call(provider: str, model: str, prompt_length: int, response_length: Optional[int] = None) -> None:
    if is_debug_enabled():
        msg = f"{provider} API call - Model: {model}, Prompt: {prompt_length} chars"
        if response_length is not None:
            msg += f", Response: {response_length} chars"
        debug_print(msg, "API")