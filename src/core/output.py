# src/core/output.py
# Output level definitions, interface protocol & registry for unified output management
# * This module is intentionally pure (no I/O) to preserve core layer integrity
# * Real implementation lives in src/cli/output_manager.py (OutputManager)
# * Registry pattern allows core modules to use output without importing CLI

from __future__ import annotations

from enum import IntEnum
from typing import Protocol, Any, runtime_checkable, Optional


# * Output verbosity levels, from least to most verbose
class OutputLevel(IntEnum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2
    DEBUG = 3


# * Protocol for output manager implementations
@runtime_checkable
class OutputInterface(Protocol):
    def get_level(self) -> OutputLevel: ...

    def is_debug_enabled(self) -> bool: ...

    def is_verbose_enabled(self) -> bool: ...

    def debug(self, msg: str, category: str = "DEBUG", **kwargs: Any) -> None: ...

    def verbose(
        self, msg: str, category: str = "INFO", detail: Optional[str] = None, **kwargs: Any
    ) -> None: ...

    def info(self, msg: str, **kwargs: Any) -> None: ...

    def debug_json(self, label: str, data: Any) -> None: ...

    def start_session(self) -> None: ...

    def end_session(self) -> None: ...


# * No-op output manager used before real manager is registered
class NullOutputManager:
    def get_level(self) -> OutputLevel:
        return OutputLevel.NORMAL

    def is_debug_enabled(self) -> bool:
        return False

    def is_verbose_enabled(self) -> bool:
        return False

    def debug(self, msg: str, category: str = "DEBUG", **kwargs: Any) -> None:
        pass

    def verbose(
        self, msg: str, category: str = "INFO", detail: Optional[str] = None, **kwargs: Any
    ) -> None:
        pass

    def info(self, msg: str, **kwargs: Any) -> None:
        pass

    def debug_json(self, label: str, data: Any) -> None:
        pass

    def start_session(self) -> None:
        pass

    def end_session(self) -> None:
        pass


_output_manager: OutputInterface = NullOutputManager()


# * Register the output manager implementation (called by CLI at startup)
def set_output_manager(manager: OutputInterface) -> None:
    global _output_manager
    _output_manager = manager


# * Get the registered output manager (safe to call from core modules)
def get_output_manager() -> OutputInterface:
    return _output_manager


# * Reset to NullOutputManager (for testing)
def reset_output_manager() -> None:
    global _output_manager
    _output_manager = NullOutputManager()
