# src/cli/output_manager.py
# Unified output management implementation for debug, verbose & quiet modes

# * Real implementation w/ Rich console output & file logging
# * Registered via set_output_manager() at CLI startup
# * Respects layering: this module can import from loom_io, config

from __future__ import annotations

import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Set

from ..core.output import OutputLevel, OutputInterface


class OutputManager:
    # Real output manager w/ console & file logging support
    # Implements OutputInterface protocol for use w/ core registry
    # Handles console output via Rich & optional file logging

    _warned_functions: Set[str] = set()  # Track deprecation warnings per-function

    def __init__(self) -> None:
        self._level = OutputLevel.NORMAL
        self._dev_mode = False
        self._session_start: float | None = None
        self._log_file_path: Path | None = None
        self._log_file_handle: Any = None

    def initialize(
        self,
        requested_level: OutputLevel = OutputLevel.NORMAL,
        dev_mode: bool = False,
        quiet: bool = False,
        log_file: Path | None = None,
    ) -> None:
        # Initialize output manager for a CLI session
        # Args: requested_level (desired output level), dev_mode (required for DEBUG),
        # quiet (forces QUIET level), log_file (optional path to write logs)
        self._dev_mode = dev_mode
        self._level = self._compute_effective_level(requested_level, dev_mode, quiet)
        self._session_start = time.time()
        self._setup_log_file(log_file)

    def _compute_effective_level(
        self, requested: OutputLevel, dev_mode: bool, quiet: bool
    ) -> OutputLevel:
        # Compute effective level w/ precedence rules
        # Precedence: 1. --quiet overrides everything -> QUIET
        # 2. DEBUG requires dev_mode -> cap at VERBOSE if not dev_mode
        # 3. Otherwise use requested level
        if quiet:
            return OutputLevel.QUIET
        max_allowed = OutputLevel.DEBUG if dev_mode else OutputLevel.VERBOSE
        return min(requested, max_allowed)

    # OutputInterface implementation

    def get_level(self) -> OutputLevel:
        return self._level

    def is_debug_enabled(self) -> bool:
        return self._level >= OutputLevel.DEBUG

    def is_verbose_enabled(self) -> bool:
        return self._level >= OutputLevel.VERBOSE

    def debug(self, msg: str, category: str = "DEBUG", **kwargs: Any) -> None:
        if self._level >= OutputLevel.DEBUG:
            from ..loom_io.console import console

            console.print(f"[debug]\\[{category}][/] {msg}", **kwargs)
            self._write_to_file(f"[{self._elapsed()}] [{category}] {msg}")

    def verbose(
        self,
        msg: str,
        category: str = "INFO",
        detail: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if self._level >= OutputLevel.VERBOSE:
            from ..loom_io.console import console

            prefix = f"[dim][{self._elapsed()}][/] [bold cyan][{category}][/]"
            console.print(f"{prefix} {msg}", **kwargs)
            if detail:
                for line in detail.split("\n"):
                    console.print(f"  [dim]{line}[/]")
            # File logging (plain text)
            self._write_to_file(f"[{self._elapsed()}] [{category}] {msg}")
            if detail:
                for line in detail.split("\n"):
                    self._write_to_file(f"  {line}")

    def info(self, msg: str, **kwargs: Any) -> None:
        if self._level >= OutputLevel.NORMAL:
            from ..loom_io.console import console

            console.print(msg, **kwargs)

    def debug_json(self, label: str, data: Any) -> None:
        if self._level >= OutputLevel.DEBUG:
            import json

            from ..loom_io.console import console

            console.print(f"[debug]\\[JSON][/] {label}:")
            console.print_json(data=data)
            # File logging (serialize to string)
            try:
                json_str = json.dumps(data, indent=2, default=str)
                self._write_to_file(f"[{self._elapsed()}] [JSON] {label}:")
                for line in json_str.split("\n"):
                    self._write_to_file(f"  {line}")
            except (TypeError, ValueError):
                self._write_to_file(f"[{self._elapsed()}] [JSON] {label}: {data}")

    def start_session(self) -> None:
        self._session_start = time.time()
        if self._log_file_handle:
            self._write_to_file(f"\n{'='*60}")
            self._write_to_file(f"Session Started: {datetime.now().isoformat()}")
            self._write_to_file(f"Level: {self._level.name}")
            if self._dev_mode:
                self._write_to_file("Mode: Developer (dev_mode enabled)")
            self._write_to_file(f"{'='*60}\n")

    def end_session(self) -> None:
        if self._log_file_handle:
            self._write_to_file(f"\n{'='*60}")
            self._write_to_file(f"Session Ended: {datetime.now().isoformat()}")
            self._write_to_file(f"{'='*60}\n")
        self.cleanup()

    # File logging

    def _elapsed(self) -> str:
        if self._session_start is None:
            return "0.00s"
        return f"{time.time() - self._session_start:.2f}s"

    def _setup_log_file(self, log_file: Path | None) -> None:
        # Close existing handle
        if self._log_file_handle is not None:
            try:
                self._log_file_handle.close()
            except Exception:
                pass
            self._log_file_handle = None

        self._log_file_path = log_file
        if log_file is not None:
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                self._log_file_handle = open(log_file, "a", encoding="utf-8")
            except Exception:
                self._log_file_path = None
                self._log_file_handle = None

    def _write_to_file(self, msg: str) -> None:
        if self._log_file_handle is not None:
            try:
                self._log_file_handle.write(f"{msg}\n")
                self._log_file_handle.flush()
            except Exception:
                pass

    def cleanup(self) -> None:
        if self._log_file_handle is not None:
            try:
                self._log_file_handle.close()
            except Exception:
                pass
            self._log_file_handle = None

    # Deprecation warning helper

    @classmethod
    def emit_deprecation_warning(cls, func_name: str, dev_mode: bool) -> None:
        # Emit opt-in deprecation warning (once per function, dev_mode only)
        # Args: func_name (deprecated function name), dev_mode (warnings only in dev_mode)
        if dev_mode and func_name not in cls._warned_functions:
            cls._warned_functions.add(func_name)
            warnings.warn(
                f"{func_name}() is deprecated. Use OutputManager directly for new code.",
                DeprecationWarning,
                stacklevel=4,
            )

    @classmethod
    def reset_warnings(cls) -> None:
        cls._warned_functions.clear()
