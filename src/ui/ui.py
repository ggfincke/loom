# src/ui/ui.py
# UI abstraction layer for progress-safe prompting & console output

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from rich.progress import Progress, SpinnerColumn, TextColumn, ProgressColumn
from rich.text import Text

from ..loom_io.console import console
from .pausable_timer import PausableTimer


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


# UI abstraction that safely coordinates console output with progress display
class UI:
    def __init__(self, progress: Progress | None = None) -> None:
        self.console = console
        self.progress = progress
        self._timer = PausableTimer()

    # pause timer and temporarily stop Progress rendering for clean prompts
    @contextmanager
    def input_mode(self):
        self._timer.pause()
        progress = self.progress
        if progress is not None:
            try:
                progress.stop()
            except Exception:
                pass
        try:
            yield
        finally:
            if progress is not None:
                try:
                    progress.start()
                except Exception:
                    pass
            self._timer.resume()

    # prompt user for input, safely pausing progress display if needed
    # when a Progress is active, route via its console so the prompt renders correctly beneath the live display
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
        # pragma: no cover - defensive
        except Exception as e:
            self.console.print(f"\nUnexpected error: {e}, defaulting to soft-fail")
            return default

    # print to console with rich formatting
    def print(self, *args, **kwargs) -> None:
        self.console.print(*args, **kwargs)

    # alias for ask() to match original interface
    def input(self, prompt: str = "", **kw) -> str | None:
        return self.ask(prompt, **kw)

    # create configured Progress instance for consistent CLI progress display
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
