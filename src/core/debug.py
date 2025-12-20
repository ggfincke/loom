# src/core/debug.py
# Debug logging utilities for verbose output & troubleshooting

from typing import Optional


# * Check if debug mode is enabled (based on dev_mode config)
def is_debug_enabled() -> bool:
    try:
        from ..config.settings import settings_manager

        settings = settings_manager.load()
        return settings.dev_mode
    except (ImportError, AttributeError):
        # fallback if settings not available
        return False


# * Print debug message if debug mode is enabled
def debug_print(message: str, category: str = "DEBUG") -> None:
    if is_debug_enabled():
        # lazy import to avoid circular dependencies
        from ..loom_io.console import console

        console.print(f"[debug]\\[{category}][/] {message}")


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
def debug_api_call(
    provider: str, model: str, prompt_length: int, response_length: Optional[int] = None
) -> None:
    if is_debug_enabled():
        msg = f"{provider} API call - Model: {model}, Prompt: {prompt_length} chars"
        if response_length is not None:
            msg += f", Response: {response_length} chars"
        debug_print(msg, "API")
