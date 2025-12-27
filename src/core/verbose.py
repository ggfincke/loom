# src/core/verbose.py
# Verbose logging utilities for debugging & troubleshooting
#
# Provides structured logging for AI calls, pipeline stages, file I/O & edit operations.
# Supports both console output & file export. Separate from dev_mode (which is for dev tools).
#
# Two modes of verbose logging:
# - Normal verbose (-v): User-focused debugging (API calls, stages, file I/O)
# - Dev verbose (dev_mode + -v): Developer-focused debugging (internal state, timing details)

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import time

# module-level state for verbose logging
_verbose_enabled: bool = False
_dev_verbose_enabled: bool = False  # dev_mode + verbose = extra dev-focused logging
_log_file_path: Optional[Path] = None
_log_file_handle: Optional[Any] = None
_session_start: Optional[float] = None


# * Initialize verbose logging for a session
def init_verbose(
    enabled: bool = False,
    log_file: Optional[Path] = None,
    dev_mode: bool = False,
) -> None:
    global _verbose_enabled, _dev_verbose_enabled, _log_file_path, _log_file_handle, _session_start

    _verbose_enabled = enabled
    _dev_verbose_enabled = enabled and dev_mode  # dev verbose requires both
    _log_file_path = log_file
    _session_start = time.time()

    # close existing file handle if any
    if _log_file_handle is not None:
        try:
            _log_file_handle.close()
        except Exception:
            pass
        _log_file_handle = None

    # open new log file if specified
    if enabled and log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            _log_file_handle = open(log_file, "a", encoding="utf-8")
            _write_to_file(f"\n{'='*60}")
            _write_to_file(f"Loom Session Started: {datetime.now().isoformat()}")
            if dev_mode:
                _write_to_file("Mode: Developer Verbose (dev_mode + verbose)")
            _write_to_file(f"{'='*60}\n")
        except Exception as e:
            # fail silently but disable file logging
            _log_file_path = None
            _log_file_handle = None
            vlog("FILE", f"Failed to open log file: {e}")


# * Check if verbose logging is enabled
def is_verbose_enabled() -> bool:
    return _verbose_enabled


# * Check if dev-mode verbose is enabled (more detailed internal logging)
def is_dev_verbose_enabled() -> bool:
    return _dev_verbose_enabled


# * Get elapsed time since session start
def _elapsed() -> str:
    if _session_start is None:
        return "0.00s"
    return f"{time.time() - _session_start:.2f}s"


# * Write message to log file (if configured)
def _write_to_file(message: str) -> None:
    if _log_file_handle is not None:
        try:
            _log_file_handle.write(f"{message}\n")
            _log_file_handle.flush()
        except Exception:
            pass


# * Core verbose logging function
def vlog(category: str, message: str, detail: Optional[str] = None) -> None:
    if not _verbose_enabled:
        return

    from ..loom_io.console import console

    timestamp = _elapsed()
    prefix = f"[dim][{timestamp}][/] [bold cyan][{category}][/]"

    # console output w/ Rich styling
    console.print(f"{prefix} {message}")
    if detail:
        # indent detail lines
        for line in detail.split("\n"):
            console.print(f"  [dim]{line}[/]")

    # file output (plain text, no Rich markup)
    plain_msg = f"[{timestamp}] [{category}] {message}"
    _write_to_file(plain_msg)
    if detail:
        for line in detail.split("\n"):
            _write_to_file(f"  {line}")


# * Log AI API call (before making the call)
def vlog_ai_request(
    provider: str,
    model: str,
    prompt_length: int,
    temperature: Optional[float] = None,
) -> None:
    temp_str = f", temp={temperature}" if temperature is not None else ""
    vlog(
        "AI",
        f"Request to {provider}",
        f"Model: {model}, Prompt: {prompt_length:,} chars{temp_str}",
    )


# * Log AI API response
def vlog_ai_response(
    provider: str,
    model: str,
    response_length: int,
    success: bool,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    duration_str = f" in {duration_ms:.0f}ms" if duration_ms else ""
    if success:
        vlog(
            "AI",
            f"Response from {provider}{duration_str}",
            f"Model: {model}, Response: {response_length:,} chars",
        )
    else:
        vlog(
            "AI",
            f"[red]Error from {provider}[/]{duration_str}",
            f"Model: {model}, Error: {error}",
        )


# * Log file read operation
def vlog_file_read(path: Path, size: Optional[int] = None) -> None:
    size_str = f" ({size:,} bytes)" if size is not None else ""
    vlog("FILE", f"Read: {path}{size_str}")


# * Log file write operation
def vlog_file_write(path: Path, size: Optional[int] = None) -> None:
    size_str = f" ({size:,} bytes)" if size is not None else ""
    vlog("FILE", f"Write: {path}{size_str}")


# * Log pipeline stage start
def vlog_stage(stage: str, description: Optional[str] = None) -> None:
    if description:
        vlog("STAGE", f"{stage}: {description}")
    else:
        vlog("STAGE", stage)


# * Log edit operation
def vlog_edit(operation: str, line: int, detail: Optional[str] = None) -> None:
    vlog("EDIT", f"{operation} at line {line}", detail)


# * Log validation result
def vlog_validation(result: str, warnings: Optional[list[str]] = None) -> None:
    if warnings:
        detail = "\n".join(f"- {w}" for w in warnings)
        vlog("VALIDATE", result, detail)
    else:
        vlog("VALIDATE", result)


# * Log configuration values being used
def vlog_config(key: str, value: Any) -> None:
    vlog("CONFIG", f"{key} = {value}")


# * Log a thought/reasoning step (for AI decision transparency)
def vlog_think(thought: str) -> None:
    vlog("THINK", thought)


# * Dev-mode only logging (for internal debugging, not user-facing)
def vlog_dev(category: str, message: str, detail: Optional[str] = None) -> None:
    if not _dev_verbose_enabled:
        return

    from ..loom_io.console import console

    timestamp = _elapsed()
    prefix = f"[dim][{timestamp}][/] [bold magenta][DEV:{category}][/]"

    # console output w/ Rich styling (magenta for dev logs)
    console.print(f"{prefix} {message}")
    if detail:
        for line in detail.split("\n"):
            console.print(f"  [dim]{line}[/]")

    # file output
    plain_msg = f"[{timestamp}] [DEV:{category}] {message}"
    _write_to_file(plain_msg)
    if detail:
        for line in detail.split("\n"):
            _write_to_file(f"  {line}")


# * Cleanup verbose logging (close file handle)
def cleanup_verbose() -> None:
    global _log_file_handle, _verbose_enabled

    if _log_file_handle is not None:
        try:
            _write_to_file(f"\n{'='*60}")
            _write_to_file(f"Session Ended: {datetime.now().isoformat()}")
            _write_to_file(f"{'='*60}\n")
            _log_file_handle.close()
        except Exception:
            pass
        _log_file_handle = None

    _verbose_enabled = False


# * Context manager for verbose logging session
class VerboseSession:
    def __init__(self, enabled: bool = False, log_file: Optional[Path] = None):
        self.enabled = enabled
        self.log_file = log_file

    def __enter__(self) -> "VerboseSession":
        init_verbose(self.enabled, self.log_file)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        cleanup_verbose()
