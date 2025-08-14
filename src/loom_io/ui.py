# src/loom_io/ui.py
# UI abstraction layer for progress-safe prompting & console output

import time
from contextlib import contextmanager
from datetime import timedelta
from rich.progress import Progress, SpinnerColumn, TextColumn, ProgressColumn
from rich.text import Text
from .console import console

# timer decoupled from Progress internals
class PausableTimer:
    def __init__(self):
        self._started_at = None
        self._paused_at = None
        self._paused_total = 0.0

    def start_if_needed(self):
        if self._started_at is None:
            self._started_at = time.monotonic()

    def pause(self):
        if self._paused_at is None:
            self._paused_at = time.monotonic()

    def resume(self):
        if self._paused_at is not None:
            self._paused_total += time.monotonic() - self._paused_at
            self._paused_at = None

    def elapsed(self) -> float:
        self.start_if_needed()
        now = self._paused_at if self._paused_at is not None else time.monotonic()
        # _started_at is guaranteed to be set by start_if_needed()
        assert self._started_at is not None
        return max(0.0, now - self._started_at - self._paused_total)

# elapsed time column that freezes while UI is in input mode
class PausableElapsedColumn(ProgressColumn):
    
    def __init__(self, timer: PausableTimer):
        super().__init__()
        self._timer = timer

    # render elapsed time in m:ss or h:mm:ss format
    def render(self, task):
        seconds = int(self._timer.elapsed())
        # h:mm:ss if >= 1h, else m:ss
        if seconds >= 3600:
            s = str(timedelta(seconds=seconds))
        else:
            s = f"{seconds // 60}:{seconds % 60:02d}"
        return Text(s, style="progress.elapsed")

# UI abstraction that safely coordinates console output w/ progress display
class UI:
    
    # init UI w/ optional progress reference for coordination
    def __init__(self, progress: Progress | None = None):
        self.console = console
        self.progress = progress
        self._timer = PausableTimer() 

    # pause just the time display; let Rich handle input w/ Live running
    @contextmanager
    def input_mode(self):
        self._timer.pause()
        try:
            yield
        finally:
            self._timer.resume()

    # prompt user for input, safely pausing progress display if needed
    def ask(self, prompt: str, *, default: str | None = "f") -> str | None:
        if not self.console.is_interactive:
            self.console.print("[dim]Input unavailable; defaulting to soft-fail[/]")
            return default
        try:
            with self.input_mode():
                return self.console.input(prompt)
        except (EOFError, KeyboardInterrupt):
            self.console.print("\nInput interrupted, defaulting to soft-fail")
            return default
        except Exception as e:
            self.console.print(f"\nUnexpected error: {e}, defaulting to soft-fail")
            return default

    # print to console w/ rich formatting
    def print(self, *args, **kwargs):
        self.console.print(*args, **kwargs)

    # alias for ask() method for convenience
    def input(self, prompt: str = "", **kw) -> str | None:
        return self.ask(prompt, **kw)

    # create configured progress instance for consistent CLI progress display
    def build_progress(self) -> Progress:
        # fresh timer each progress session so elapsed resets correctly
        self._timer = PausableTimer()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            PausableElapsedColumn(self._timer),
            refresh_per_second=8,
            console=self.console,
            transient=False,
        )
        return self.progress