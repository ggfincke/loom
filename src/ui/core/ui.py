# src/ui/core/ui.py
# UI abstraction layer for progress-safe prompting & console output

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from typing import Generator, Any
from .rich_components import Progress, SpinnerColumn, TextColumn, ProgressColumn, Text

from ...loom_io.console import get_console
from .pausable_timer import PausableTimer
from ..theming.colors import LoomColors


# elapsed time column that freezes while UI is in input mode
class PausableElapsedColumn(ProgressColumn):
    def __init__(self, timer: PausableTimer):
        super().__init__()
        self._timer = timer

    # render elapsed time in m:ss or h:mm:ss format
    def render(self, task: Any) -> Text:
        seconds = int(self._timer.elapsed())
        
        # h:mm:ss if >= 1h, else m:ss
        if seconds >= 3600:
            s = str(timedelta(seconds=seconds))
        else:
            s = f"{seconds // 60}:{seconds % 60:02d}"
        return Text(s, style="progress.elapsed")


# UI abstraction that safely coordinates console output w/ progress display
class UI:
    def __init__(self, progress: Progress | None = None) -> None:
        self.progress = progress
        self._timer = PausableTimer()
        # initialize console reference to global instance (allows test mocking)
        self.console = get_console()

    # pause timer & temporarily stop Progress rendering for clean prompts
    @contextmanager
    def input_mode(self) -> Generator[None, None, None]:
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
    def ask(self, prompt: str, *, default: str | None = "s") -> str | None:
        if not self.console.is_interactive:
            self.console.print("[dim]Input unavailable; defaulting to (s)oft-fail[/]")
            return default
        try:
            with self.input_mode():
                styled_prompt = f"[loom.accent]{prompt}[/]"
                return self.console.input(styled_prompt)
        except (EOFError, KeyboardInterrupt):
            self.console.print("\n[warning]Input interrupted, defaulting to (s)oft-fail[/]")
            return default
        # pragma: no cover - defensive
        except Exception as e:
            self.console.print(f"\n[error]Unexpected error: {e}, defaulting to (s)oft-fail[/]")
            return default

    # print to console w/ rich formatting
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
            SpinnerColumn(spinner_name="dots", style=LoomColors.ACCENT_SECONDARY),
            TextColumn("[progress.description]{task.description}"),
            PausableElapsedColumn(self._timer),
            refresh_per_second=8,
            console=self.console,
            transient=False,
        )
        return self.progress
