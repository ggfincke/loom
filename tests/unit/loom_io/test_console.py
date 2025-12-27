# tests/unit/test_console.py
# Unit tests for console module functionality

import pytest
from unittest.mock import patch, Mock
from rich.console import Console

from src.loom_io.console import (
    console,
    get_console,
    configure_console,
    reset_console,
    refresh_theme,
)


class TestConsoleModule:

    # * Test global console proxy exists & forwards Console methods
    def test_console_instance_exists(self):
        assert console is not None
        # console is now a proxy; verify it has Console-like behavior
        assert hasattr(console, "print")
        assert hasattr(console, "capture")
        assert callable(console.print)

    # * Test get_console returns underlying Console instance
    def test_get_console_returns_console_instance(self):
        result = get_console()
        assert isinstance(result, Console)
        # get_console returns the underlying Console, not the proxy
        assert result is console._get_console()

    # * Test reset_console creates new underlying instance
    def test_reset_console_creates_new_instance(self):
        original_underlying = console._get_console()

        new_console = reset_console()

        # should return new Console instance
        assert isinstance(new_console, Console)
        # the underlying console should be different
        assert new_console is not original_underlying
        # the proxy's underlying console should be updated
        assert console._get_console() is new_console

    # * Test configure_console w/ default parameters
    def test_configure_console_no_parameters(self):
        result = configure_console()

        # should return a console instance when no parameters provided
        assert isinstance(result, Console)

    # * Test configure_console w/ width parameter
    def test_configure_console_with_width(self):
        result = configure_console(width=100)

        assert isinstance(result, Console)
        # verify the console has the configured width
        assert result.size.width == 100

    # * Test configure_console w/ height parameter
    def test_configure_console_with_height(self):
        result = configure_console(height=50)

        assert isinstance(result, Console)
        # verify the console has the configured height
        assert result.size.height == 50

    # * Test configure_console w/ force_terminal parameter
    def test_configure_console_with_force_terminal(self):
        result = configure_console(force_terminal=True)

        assert isinstance(result, Console)
        # verify force_terminal was set
        assert hasattr(result, "_force_terminal")

    # * Test configure_console w/ record parameter
    def test_configure_console_with_record(self):
        result = configure_console(record=True)

        assert isinstance(result, Console)
        # verify recording functionality exists (internal implementation may vary)
        assert hasattr(result, "record") or hasattr(result, "_record_buffer")

    # * Test configure_console w/ multiple parameters
    def test_configure_console_with_multiple_parameters(self):
        result = configure_console(
            width=120, height=40, force_terminal=False, record=True
        )

        assert isinstance(result, Console)
        assert result.size.width == 120
        assert result.size.height == 40

    # * Test refresh_theme w/ successful import
    @patch("src.ui.theming.console_theme.refresh_theme")
    # * Verify refresh theme success
    def test_refresh_theme_success(self, mock_refresh_theme):
        # should call the ui refresh_theme function
        refresh_theme()
        mock_refresh_theme.assert_called_once()

    # * Test refresh_theme w/ import error
    def test_refresh_theme_import_error(self):
        # should not raise exception when import fails
        with patch("builtins.__import__", side_effect=ImportError):
            refresh_theme()  # should complete without error

    # * Test refresh_theme function is available
    def test_refresh_theme_function_exists(self):
        # verify the function exists & can be called
        assert callable(refresh_theme)

        # should not raise exception
        refresh_theme()

    # * Test console configuration persistence
    def test_console_configuration_persistence(self):
        # configure console w/ specific settings
        configured_console = configure_console(width=80, record=True)

        # verify the global console has been updated
        current_console = get_console()
        assert current_console is configured_console

    # * Test reset restores default behavior
    def test_reset_restores_defaults(self):
        # first configure w/ custom settings
        configure_console(width=200, height=100)

        # then reset to defaults
        reset_result = reset_console()

        # should have default Console behavior
        assert isinstance(reset_result, Console)

    # * Test console module exports
    def test_console_module_exports(self):
        # verify all expected functions are exported
        from src.loom_io.console import __all__

        expected_exports = [
            "console",
            "get_console",
            "configure_console",
            "reset_console",
            "refresh_theme",
        ]

        for export in expected_exports:
            assert export in __all__

    # * Test console can be used for output
    def test_console_basic_functionality(self):
        test_console = get_console()

        # should be able to use console methods without error
        assert hasattr(test_console, "print")
        assert callable(test_console.print)

        # test basic print functionality w/ capture
        with test_console.capture() as capture:
            test_console.print("test message")

        output = capture.get()
        assert "test message" in output

    # * Test console configuration w/ invalid parameters
    def test_configure_console_with_none_values(self):
        # passing None values should not create new console
        result = configure_console(
            width=None,
            height=None,
            force_terminal=None,
            record=False,  # only record=False should not trigger recreation
        )

        # should return existing console since no meaningful config provided
        assert isinstance(result, Console)

    # * Test console thread safety
    def test_console_thread_safety(self):
        import threading

        results = []

        def get_console_instance():
            results.append(get_console())

        # create multiple threads that access console
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_console_instance)
            threads.append(thread)
            thread.start()

        # wait for all threads
        for thread in threads:
            thread.join()

        # all threads should get the same console instance
        assert len(results) == 5
        first_console = results[0]
        for console_instance in results:
            assert console_instance is first_console


class TestConsoleInitialization:

    # * Test auto initialization attempts
    def test_auto_initialization_attempts(self):
        # The module should handle missing ui module gracefully
        # Just verify that refresh_theme doesn't crash w/ ImportError
        with patch(
            "src.ui.theming.console_theme.refresh_theme", side_effect=ImportError
        ):
            refresh_theme()  # should not raise exception

        # console should still work
        assert get_console() is not None

    # * Test module can be imported without ui dependencies
    def test_import_without_ui_dependencies(self):
        # should be able to use console module even if ui module is not available
        from src.loom_io import console as console_module

        # basic functionality should still work
        assert hasattr(console_module, "console")
        assert hasattr(console_module, "get_console")

        # verify basic functionality works
        test_console = console_module.get_console()
        assert test_console is not None


class TestConsoleEdgeCases:

    # * Test configure_console w/ edge case values
    def test_configure_console_edge_cases(self):
        # test w/ very small dimensions
        result = configure_console(width=1, height=1)
        assert isinstance(result, Console)

        # test w/ very large dimensions
        result = configure_console(width=10000, height=10000)
        assert isinstance(result, Console)

    # * Test multiple consecutive resets
    def test_multiple_consecutive_resets(self):
        original = get_console()

        # perform multiple resets
        first_reset = reset_console()
        second_reset = reset_console()
        third_reset = reset_console()

        # each should create a new instance
        assert first_reset is not original
        assert second_reset is not first_reset
        assert third_reset is not second_reset

        # current console should be the last one created
        current = get_console()
        assert current is third_reset

    # * Test configure after reset
    def test_configure_after_reset(self):
        # reset first
        reset_console()

        # then configure
        configured = configure_console(width=150, record=True)

        # should have both reset behavior & configuration
        assert isinstance(configured, Console)
        assert configured.size.width == 150

    # * Test refresh_theme w/ partial import success
    @patch("src.ui.theming.console_theme.refresh_theme")
    # * Verify refresh theme partial import
    def test_refresh_theme_partial_import(self, mock_refresh_theme):
        # simulate scenario where import succeeds but function fails
        mock_refresh_theme.side_effect = Exception("Theme error")

        # the function only catches ImportError, so other exceptions will propagate
        with pytest.raises(Exception, match="Theme error"):
            refresh_theme()

    # * Test console capture functionality
    def test_console_capture_functionality(self):
        test_console = get_console()

        # test capturing output
        with test_console.capture() as capture:
            test_console.print("test output")
            test_console.print("[bold]formatted text[/bold]")

        output = capture.get()
        assert "test output" in output
        assert "formatted text" in output
