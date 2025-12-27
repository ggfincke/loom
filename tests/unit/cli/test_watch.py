# tests/unit/cli/test_watch.py
# Unit tests for the watch module (file watching & automatic re-run)

from __future__ import annotations

import time
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock, patch

import pytest

from src.cli.watch import DebouncedHandler, WatchRunner


# Tests for DebouncedHandler class.
class TestDebouncedHandler:

    # Handler should ignore events for files not in watched paths.
    # * Verify filters unwatched paths
    def test_filters_unwatched_paths(self, tmp_path: Path):
        watched_file = tmp_path / "watched.txt"
        unwatched_file = tmp_path / "unwatched.txt"
        watched_file.touch()
        unwatched_file.touch()

        callback = MagicMock()
        handler = DebouncedHandler({watched_file}, callback, debounce=0.1)

        # create mock event for unwatched file
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = str(unwatched_file)

        handler.on_modified(mock_event)

        # callback should not be called for unwatched file
        time.sleep(0.2)
        callback.assert_not_called()

    # Handler should ignore directory modification events.
    # * Verify ignores directory events
    def test_ignores_directory_events(self, tmp_path: Path):
        watched_file = tmp_path / "watched.txt"
        watched_file.touch()

        callback = MagicMock()
        handler = DebouncedHandler({watched_file}, callback, debounce=0.1)

        # create mock event for directory
        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = str(tmp_path)

        handler.on_modified(mock_event)

        time.sleep(0.2)
        callback.assert_not_called()

    # Handler should trigger callback for watched file changes.
    # * Verify triggers callback for watched file
    def test_triggers_callback_for_watched_file(self, tmp_path: Path):
        watched_file = tmp_path / "watched.txt"
        watched_file.touch()

        callback = MagicMock()
        handler = DebouncedHandler({watched_file}, callback, debounce=0.1)

        # create mock event for watched file
        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = str(watched_file)

        handler.on_modified(mock_event)

        # wait for debounce
        time.sleep(0.2)
        callback.assert_called_once()

    # Handler should debounce rapid file changes.
    # * Verify debounces rapid changes
    def test_debounces_rapid_changes(self, tmp_path: Path):
        watched_file = tmp_path / "watched.txt"
        watched_file.touch()

        callback = MagicMock()
        handler = DebouncedHandler({watched_file}, callback, debounce=0.3)

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = str(watched_file)

        # fire multiple events rapidly
        handler.on_modified(mock_event)
        time.sleep(0.1)
        handler.on_modified(mock_event)
        time.sleep(0.1)
        handler.on_modified(mock_event)

        # wait for debounce to complete
        time.sleep(0.5)

        # callback should only be called once (debounced)
        assert callback.call_count == 1

    # Handler should catch & log callback errors without crashing.
    # * Verify handles callback errors
    def test_handles_callback_errors(self, tmp_path: Path):
        watched_file = tmp_path / "watched.txt"
        watched_file.touch()

        callback = MagicMock(side_effect=Exception("Test error"))
        handler = DebouncedHandler({watched_file}, callback, debounce=0.1)

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = str(watched_file)

        # should not raise
        handler.on_modified(mock_event)
        time.sleep(0.2)

        callback.assert_called_once()


# Tests for WatchRunner class.
class TestWatchRunner:

    # WatchRunner should filter out None paths.
    # * Verify filters none paths
    def test_filters_none_paths(self, tmp_path: Path):
        valid_file = tmp_path / "valid.txt"
        valid_file.touch()

        runner = WatchRunner([valid_file, None, None], lambda: None, debounce=1.0)

        assert len(runner.paths) == 1
        assert runner.paths[0] == valid_file

    # WatchRunner should filter out non-existent paths.
    # * Verify filters nonexistent paths
    def test_filters_nonexistent_paths(self, tmp_path: Path):
        valid_file = tmp_path / "valid.txt"
        invalid_file = tmp_path / "nonexistent.txt"
        valid_file.touch()

        runner = WatchRunner([valid_file, invalid_file], lambda: None, debounce=1.0)

        assert len(runner.paths) == 1
        assert runner.paths[0] == valid_file

    # WatchRunner should handle empty path list gracefully.
    # * Verify handles empty paths
    def test_handles_empty_paths(self, tmp_path: Path, capsys):
        runner = WatchRunner([], lambda: None, debounce=1.0)

        # start should return early without crashing
        runner.start()

        # should print error message
        captured = capsys.readouterr()
        assert "No valid paths to watch" in captured.out

    # WatchRunner should run the command once immediately on start.
    # * Verify runs initial command
    def test_runs_initial_command(self, tmp_path: Path):
        valid_file = tmp_path / "valid.txt"
        valid_file.touch()

        callback = MagicMock()
        runner = WatchRunner([valid_file], callback, debounce=1.0)

        # mock the observer to avoid blocking
        with patch.object(runner, "_observer", None):
            with patch("src.cli.watch.Observer") as mock_observer_class:
                mock_observer = MagicMock()
                mock_observer.is_alive.return_value = False
                mock_observer_class.return_value = mock_observer

                runner.start()

        # callback should be called for initial run
        callback.assert_called_once()

    # WatchRunner should handle errors in initial command run.
    # * Verify handles initial command error
    def test_handles_initial_command_error(self, tmp_path: Path):
        valid_file = tmp_path / "valid.txt"
        valid_file.touch()

        callback = MagicMock(side_effect=Exception("Initial run error"))
        runner = WatchRunner([valid_file], callback, debounce=1.0)

        # should not raise
        with patch("src.cli.watch.Observer") as mock_observer_class:
            mock_observer = MagicMock()
            mock_observer.is_alive.return_value = False
            mock_observer_class.return_value = mock_observer

            runner.start()

        callback.assert_called_once()


# Tests for watch-related settings.
class TestWatchSettings:

    # Default watch_debounce should be 1.0 seconds.
    # * Verify watch debounce default
    def test_watch_debounce_default(self):
        from src.config.settings import LoomSettings

        settings = LoomSettings()
        assert settings.watch_debounce == 1.0

    # watch_debounce below 0.1 should raise ValueError.
    # * Verify watch debounce validation too low
    def test_watch_debounce_validation_too_low(self):
        from src.config.settings import LoomSettings

        with pytest.raises(ValueError, match="watch_debounce must be >= 0.1"):
            LoomSettings(watch_debounce=0.05)

    # Custom watch_debounce >= 0.1 should be accepted.
    # * Verify watch debounce valid custom
    def test_watch_debounce_valid_custom(self):
        from src.config.settings import LoomSettings

        settings = LoomSettings(watch_debounce=2.5)
        assert settings.watch_debounce == 2.5
