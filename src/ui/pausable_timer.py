# src/ui/pausable_timer.py
# Pausable timer utility used by UI progress display

from __future__ import annotations

import time

# pausable timer implementation for UI progress tracking
class PausableTimer:
    def __init__(self) -> None:
        self._started_at: float | None = None
        self._paused_at: float | None = None
        self._paused_total: float = 0.0

    # start timer if not already started
    def start_if_needed(self) -> None:
        if self._started_at is None:
            self._started_at = time.monotonic()

    # pause the timer
    def pause(self) -> None:
        if self._paused_at is None:
            self._paused_at = time.monotonic()

    # resume the timer after pause
    def resume(self) -> None:
        if self._paused_at is not None:
            self._paused_total += time.monotonic() - self._paused_at
            self._paused_at = None

    # get elapsed time in seconds (excluding paused time)
    def elapsed(self) -> float:
        self.start_if_needed()
        now = self._paused_at if self._paused_at is not None else time.monotonic()
        
        # _started_at is guaranteed to be set by start_if_needed()
        assert self._started_at is not None
        return max(0.0, now - self._started_at - self._paused_total)

