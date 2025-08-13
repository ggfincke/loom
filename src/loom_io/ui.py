# src/loom_io/ui.py
# UI abstraction layer for progress-safe prompting & console output

import sys
from .console import console

# UI abstraction that safely coordinates console output w/ progress display
class UI:
    
    def __init__(self, progress=None):
        # init UI w/ optional progress reference for coordination
        self.console = console
        self.progress = progress
    
    def ask(self, prompt: str) -> str:
        # prompt user for input, safely pausing progress display if needed
        if not sys.stdin.isatty():
            self.console.print("[dim]Input unavailable; defaulting to fail-soft[/]")
            return "f"
        
        # stop live rendering during input to prevent interference
        if self.progress and self.progress.live.is_started:
            self.progress.live.stop()
            try:
                return self.console.input(prompt)
            except (EOFError, KeyboardInterrupt):
                self.console.print("\nInput interrupted, defaulting to fail-soft")
                return "f"
            except Exception as e:
                self.console.print(f"\nUnexpected error: {e}, defaulting to fail-soft")
                return "f"
            finally:
                self.progress.live.start()
        else:
            # no progress to coordinate with, use console directly
            try:
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