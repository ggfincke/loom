# src/cli/watch.py
# File watcher for automatic re-run on input file changes

from __future__ import annotations

import signal
import sys
from pathlib import Path
from threading import Timer
from typing import Callable

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..loom_io.console import console


# file event handler w/ debounce to avoid rapid re-triggers
class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, paths: set[Path], callback: Callable[[], None], debounce: float):
        self.paths = {p.resolve() for p in paths}
        self.callback = callback
        self.debounce = debounce
        self._timer: Timer | None = None

    def on_modified(self, event) -> None:
        if event.is_directory:
            return

        event_path = Path(event.src_path).resolve()
        if event_path not in self.paths:
            return

        # cancel existing timer & start new one (debounce)
        if self._timer:
            self._timer.cancel()

        self._timer = Timer(self.debounce, self._trigger, args=[event_path])
        self._timer.start()

    def _trigger(self, changed_path: Path) -> None:
        console.print(f"\n[dim]--- {changed_path.name} changed ---[/]\n")
        try:
            self.callback()
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
        self._print_watching_status()

    def _print_watching_status(self) -> None:
        console.print("\n[cyan]Watching for changes...[/] [dim](Ctrl+C to stop)[/]")


# wraps command execution w/ file watching for automatic re-run
class WatchRunner:
    def __init__(
        self,
        paths: list[Path],
        run_command: Callable[[], None],
        debounce: float = 1.0,
    ):
        # filter to valid, existing paths
        self.paths = [p for p in paths if p is not None and p.exists()]
        self.run_command = run_command
        self.debounce = debounce
        self._observer: Observer | None = None

    # run command once, then watch for changes & block until Ctrl+C
    def start(self) -> None:
        if not self.paths:
            console.print("[red]Error: No valid paths to watch[/]")
            return

        # initial run
        try:
            self.run_command()
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")

        # setup watcher
        handler = DebouncedHandler(set(self.paths), self.run_command, self.debounce)
        observer = Observer()
        self._observer = observer

        # watch parent directories of each file
        watched_dirs: set[Path] = set()
        for path in self.paths:
            parent = path.resolve().parent
            if parent not in watched_dirs:
                observer.schedule(handler, str(parent), recursive=False)
                watched_dirs.add(parent)

        # setup clean shutdown
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        def shutdown(signum, frame):
            console.print("\n[dim]Stopping watch...[/]")
            observer.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        console.print("\n[cyan]Watching for changes...[/] [dim](Ctrl+C to stop)[/]")
        console.print(f"[dim]   Files: {', '.join(p.name for p in self.paths)}[/]")

        observer.start()

        # block until interrupted
        try:
            while observer.is_alive():
                observer.join(timeout=1)
        except KeyboardInterrupt:
            pass
        finally:
            # restore original signal handlers
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
            observer.stop()
            observer.join()
