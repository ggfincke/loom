# src/loom_io/ui.py
# UI abstraction layer for progress-safe prompting & console output

import sys
from contextlib import contextmanager
from .console import console

# UI abstraction that safely coordinates console output w/ progress display
class UI:
    
    def __init__(self, progress=None):
        # init UI w/ optional progress reference for coordination
        self.console = console
        self.progress = progress
    
    @contextmanager
    def input_mode(self):
        # context manager for safe user input w/ progress coordination
        if not sys.stdin.isatty():
            raise RuntimeError("Input mode not available (not a TTY)")
        
        # stop live rendering during input to prevent interference
        progress_was_running = False
        if self.progress and self.progress.live.is_started:
            progress_was_running = True
            self.progress.live.stop()
        
        try:
            yield
        finally:
            # ensure progress is resumed if it was previously running
            if progress_was_running and self.progress:
                self.progress.live.start()
    
    def ask(self, prompt: str) -> str:
        # prompt user for input, safely pausing progress display if needed
        if not sys.stdin.isatty():
            self.console.print("[dim]Input unavailable; defaulting to fail-soft[/]")
            return "f"
        
        try:
            with self.input_mode():
                return self.console.input(prompt)
        except (EOFError, KeyboardInterrupt):
            self.console.print("\nInput interrupted, defaulting to fail-soft")
            return "f"
        except Exception as e:
            self.console.print(f"\nUnexpected error: {e}, defaulting to fail-soft")
            return "f"
    
    # print to console with rich formatting
    def print(self, *args, **kwargs):
        self.console.print(*args, **kwargs)
    
    # alias for ask() method for convenience
    def input(self, prompt: str = "") -> str:
        return self.ask(prompt)