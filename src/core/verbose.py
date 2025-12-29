# src/core/verbose.py
# Verbose logging utilities - delegates to unified OutputManager w/ structured logging for AI calls, pipeline stages, file I/O & edit operations

from __future__ import annotations

from pathlib import Path
from typing import Any

from .output import get_output_manager, set_output_manager, OutputLevel


# * Initialize verbose logging for a session
def init_verbose(
    enabled: bool = False,
    log_file: Path | None = None,
    dev_mode: bool = False,
) -> None:
    if enabled and dev_mode:
        requested_level = OutputLevel.DEBUG
    elif enabled:
        requested_level = OutputLevel.VERBOSE
    else:
        requested_level = OutputLevel.NORMAL

    try:
        from ..cli.output_manager import OutputManager

        manager = OutputManager()
        manager.initialize(
            requested_level=requested_level,
            dev_mode=dev_mode,
            log_file=log_file,
        )
        set_output_manager(manager)
    except ImportError:
        pass


# * Check if verbose logging is enabled
def is_verbose_enabled() -> bool:
    return get_output_manager().is_verbose_enabled()


# * Check if dev-mode verbose is enabled
def is_dev_verbose_enabled() -> bool:
    return get_output_manager().is_debug_enabled()


# * Core verbose logging function
def vlog(category: str, message: str, detail: str | None = None) -> None:
    get_output_manager().verbose(message, category, detail)


# * Log AI API call (before making the call)
def vlog_ai_request(
    provider: str,
    model: str,
    prompt_length: int,
    temperature: float | None = None,
) -> None:
    temp_str = f", temp={temperature}" if temperature is not None else ""
    detail = f"Model: {model}, Prompt: {prompt_length:,} chars{temp_str}"
    get_output_manager().verbose(f"Request to {provider}", "AI", detail)


# * Log AI API response
def vlog_ai_response(
    provider: str,
    model: str,
    response_length: int,
    success: bool,
    duration_ms: float | None = None,
    error: str | None = None,
) -> None:
    duration_str = f" in {duration_ms:.0f}ms" if duration_ms else ""
    if success:
        detail = f"Model: {model}, Response: {response_length:,} chars"
        get_output_manager().verbose(
            f"Response from {provider}{duration_str}", "AI", detail
        )
    else:
        detail = f"Model: {model}, Error: {error}"
        get_output_manager().verbose(
            f"[red]Error from {provider}[/]{duration_str}", "AI", detail
        )


# * Log file read operation
def vlog_file_read(path: Path, size: int | None = None) -> None:
    size_str = f" ({size:,} bytes)" if size is not None else ""
    get_output_manager().verbose(f"Read: {path}{size_str}", "FILE")


# * Log file write operation
def vlog_file_write(path: Path, size: int | None = None) -> None:
    size_str = f" ({size:,} bytes)" if size is not None else ""
    get_output_manager().verbose(f"Write: {path}{size_str}", "FILE")


# * Log pipeline stage start
def vlog_stage(stage: str, description: str | None = None) -> None:
    if description:
        get_output_manager().verbose(f"{stage}: {description}", "STAGE")
    else:
        get_output_manager().verbose(stage, "STAGE")


# * Log edit operation
def vlog_edit(operation: str, line: int, detail: str | None = None) -> None:
    get_output_manager().verbose(f"{operation} at line {line}", "EDIT", detail)


# * Log validation result
def vlog_validation(result: str, warnings: list[str] | None = None) -> None:
    if warnings:
        detail = "\n".join(f"- {w}" for w in warnings)
        get_output_manager().verbose(result, "VALIDATE", detail)
    else:
        get_output_manager().verbose(result, "VALIDATE")


# * Log configuration values being used
def vlog_config(key: str, value: Any) -> None:
    get_output_manager().verbose(f"{key} = {value}", "CONFIG")


# * Log a thought/reasoning step
def vlog_think(thought: str) -> None:
    get_output_manager().verbose(thought, "THINK")


# * Dev-mode only logging
def vlog_dev(category: str, message: str, detail: str | None = None) -> None:
    # Only output at DEBUG level
    if get_output_manager().is_debug_enabled():
        get_output_manager().verbose(message, f"DEV:{category}", detail)


# * Cleanup verbose logging
def cleanup_verbose() -> None:
    get_output_manager().end_session()


# * Context manager for verbose logging session
class VerboseSession:
    def __init__(
        self,
        enabled: bool = False,
        log_file: Path | None = None,
        dev_mode: bool = False,
    ):
        self.enabled = enabled
        self.log_file = log_file
        self.dev_mode = dev_mode

    def __enter__(self) -> "VerboseSession":
        init_verbose(self.enabled, self.log_file, self.dev_mode)
        get_output_manager().start_session()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        get_output_manager().end_session()
