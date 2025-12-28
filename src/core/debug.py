# src/core/debug.py
# Debug logging utilities - delegates to unified OutputManager

from .output import get_output_manager


# * Check if debug mode is enabled (based on output level)
def is_debug_enabled() -> bool:
    return get_output_manager().is_debug_enabled()


# * Print debug message if debug mode is enabled
def debug_print(message: str, category: str = "DEBUG") -> None:
    get_output_manager().debug(message, category)


# * Print AI-related debug information
def debug_ai(message: str) -> None:
    get_output_manager().debug(message, "AI")


# * Print error details in debug mode
def debug_error(error: Exception, context: str = "") -> None:
    error_msg = f"Exception: {type(error).__name__}: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    get_output_manager().debug(error_msg, "ERROR")


# * Debug API request/response details
def debug_api_call(
    provider: str, model: str, prompt_length: int, response_length: int | None = None
) -> None:
    msg = f"{provider} API call - Model: {model}, Prompt: {prompt_length} chars"
    if response_length is not None:
        msg += f", Response: {response_length} chars"
    get_output_manager().debug(msg, "API")
