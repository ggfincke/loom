# tests/unit/core/test_debug.py
# Unit tests for debug logging utilities

import pytest
from unittest.mock import patch, Mock

from src.core.debug import (
    is_debug_enabled,
    debug_print,
    debug_ai,
    debug_error,
    debug_api_call,
)


# * Tests for is_debug_enabled() function


class TestIsDebugEnabled:
    """Tests for is_debug_enabled() function."""

    def test_delegates_to_dev_mode(self, isolate_config):
        """is_debug_enabled delegates to is_dev_mode_enabled."""
        # patch at source since it's imported inside the function
        with patch("src.config.dev_mode.is_dev_mode_enabled") as mock_check:
            mock_check.return_value = True

            result = is_debug_enabled()

            mock_check.assert_called_once()
            assert result is True

    def test_returns_false_by_default(self, isolate_config):
        """Returns False when dev_mode is disabled."""
        assert is_debug_enabled() is False

    def test_returns_true_when_dev_mode_enabled(self, dev_mode_enabled):
        """Returns True when dev_mode is enabled."""
        assert is_debug_enabled() is True


# * Tests for debug_print() function


class TestDebugPrint:
    """Tests for debug_print() function."""

    def test_prints_when_debug_enabled(self, dev_mode_enabled):
        """Prints debug message when debug mode is enabled."""
        # patch console at source location
        with patch("src.loom_io.console.console") as mock_console:
            debug_print("test message", "TEST")

            mock_console.print.assert_called_once()
            call_arg = mock_console.print.call_args[0][0]
            assert "[TEST]" in call_arg
            assert "test message" in call_arg

    def test_silent_when_debug_disabled(self, isolate_config):
        """Does not print when debug mode is disabled."""
        with patch("src.loom_io.console.console") as mock_console:
            debug_print("test message")

            mock_console.print.assert_not_called()

    def test_default_category_is_debug(self, dev_mode_enabled):
        """Default category is DEBUG."""
        with patch("src.loom_io.console.console") as mock_console:
            debug_print("test message")

            call_arg = mock_console.print.call_args[0][0]
            assert "[DEBUG]" in call_arg


# * Tests for debug_ai() function


class TestDebugAi:
    """Tests for debug_ai() helper."""

    def test_uses_ai_category(self, dev_mode_enabled):
        """debug_ai uses 'AI' as category."""
        with patch("src.core.debug.debug_print") as mock_print:
            debug_ai("model response")

            mock_print.assert_called_once_with("model response", "AI")

    def test_silent_when_debug_disabled(self, isolate_config):
        """Does not print when debug mode is disabled."""
        with patch("src.loom_io.console.console") as mock_console:
            debug_ai("model response")

            mock_console.print.assert_not_called()


# * Tests for debug_error() function


class TestDebugError:
    """Tests for debug_error() function."""

    def test_formats_exception(self, dev_mode_enabled):
        """Formats exception type and message."""
        with patch("src.core.debug.debug_print") as mock_print:
            error = ValueError("test error")
            debug_error(error)

            call_arg = mock_print.call_args[0][0]
            assert "ValueError" in call_arg
            assert "test error" in call_arg

    def test_includes_context(self, dev_mode_enabled):
        """Includes context when provided."""
        with patch("src.core.debug.debug_print") as mock_print:
            error = ValueError("test error")
            debug_error(error, "during parsing")

            call_arg = mock_print.call_args[0][0]
            assert "during parsing" in call_arg

    def test_uses_error_category(self, dev_mode_enabled):
        """Uses ERROR as category."""
        with patch("src.core.debug.debug_print") as mock_print:
            debug_error(ValueError("test"))

            assert mock_print.call_args[0][1] == "ERROR"

    def test_silent_when_debug_disabled(self, isolate_config):
        """Does not print when debug mode is disabled."""
        with patch("src.loom_io.console.console") as mock_console:
            debug_error(ValueError("test"))

            mock_console.print.assert_not_called()


# * Tests for debug_api_call() function


class TestDebugApiCall:
    """Tests for debug_api_call() function."""

    def test_formats_api_call_info(self, dev_mode_enabled):
        """Formats API call information."""
        with patch("src.core.debug.debug_print") as mock_print:
            debug_api_call("openai", "gpt-4o", 1000, 500)

            call_arg = mock_print.call_args[0][0]
            assert "openai" in call_arg
            assert "gpt-4o" in call_arg
            assert "1000" in call_arg
            assert "500" in call_arg

    def test_handles_no_response_length(self, dev_mode_enabled):
        """Works without response length."""
        with patch("src.core.debug.debug_print") as mock_print:
            debug_api_call("anthropic", "claude-3", 2000)

            mock_print.assert_called_once()
            call_arg = mock_print.call_args[0][0]
            assert "anthropic" in call_arg
            assert "2000" in call_arg

    def test_uses_api_category(self, dev_mode_enabled):
        """Uses API as category."""
        with patch("src.core.debug.debug_print") as mock_print:
            debug_api_call("openai", "gpt-4o", 1000)

            assert mock_print.call_args[0][1] == "API"

    def test_silent_when_debug_disabled(self, isolate_config):
        """Does not print when debug mode is disabled."""
        with patch("src.loom_io.console.console") as mock_console:
            debug_api_call("openai", "gpt-4o", 1000)

            mock_console.print.assert_not_called()
