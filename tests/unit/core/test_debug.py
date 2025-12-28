# tests/unit/core/test_debug.py
# Unit tests for debug logging utilities
#
# These tests verify the debug functions work correctly w/ the new
# OutputManager architecture while maintaining backward compatibility.

import pytest
from unittest.mock import patch, MagicMock

from src.core.debug import (
    is_debug_enabled,
    debug_print,
    debug_ai,
    debug_error,
    debug_api_call,
)
from src.core.output import (
    OutputLevel,
    set_output_manager,
    reset_output_manager,
    get_output_manager,
)
from src.cli.output_manager import OutputManager

@pytest.fixture
def debug_output_manager():
    
    manager = OutputManager()
    manager.initialize(requested_level=OutputLevel.DEBUG, dev_mode=True)
    set_output_manager(manager)
    yield manager
    reset_output_manager()

@pytest.fixture
def normal_output_manager():
    
    manager = OutputManager()
    manager.initialize(requested_level=OutputLevel.NORMAL, dev_mode=False)
    set_output_manager(manager)
    yield manager
    reset_output_manager()

# * Tests for is_debug_enabled() function

class TestIsDebugEnabled:

    # * Verify returns true when output level is DEBUG
    # * Returns True when output level is DEBUG.
    def test_returns_true_at_debug_level(self, debug_output_manager):
        assert is_debug_enabled() is True

    # * Verify returns false by default (NullOutputManager)
    # * Returns False w/ NullOutputManager (default).
    def test_returns_false_by_default(self, isolate_config):
        reset_output_manager()
        assert is_debug_enabled() is False

    # * Verify returns false at NORMAL level
    # * Returns False when output level is NORMAL.
    def test_returns_false_at_normal_level(self, normal_output_manager):
        assert is_debug_enabled() is False

    # * Verify delegates to output manager
    # * Delegates to get_output_manager().is_debug_enabled().
    def test_delegates_to_output_manager(self, isolate_config):
        mock_manager = MagicMock()
        mock_manager.is_debug_enabled.return_value = True
        set_output_manager(mock_manager)

        result = is_debug_enabled()

        mock_manager.is_debug_enabled.assert_called_once()
        assert result is True
        reset_output_manager()

# * Tests for debug_print() function

class TestDebugPrint:

    # * Verify prints when debug enabled
    # * Prints debug message when debug level is enabled.
    def test_prints_when_debug_enabled(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_print("test message", "TEST")

            # Check that our call was made (may have other calls from setup)
            assert mock_console.print.called
            # Find our specific call in the call list
            call_args = [str(call) for call in mock_console.print.call_args_list]
            matching = [c for c in call_args if "[TEST]" in c and "test message" in c]
            assert len(matching) == 1, f"Expected one matching call, got: {call_args}"

    # * Verify silent when debug disabled
    # * Does not print when debug level is not enabled.
    def test_silent_when_debug_disabled(self, normal_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_print("test message")

            mock_console.print.assert_not_called()

    # * Verify default category is DEBUG
    # * Default category is DEBUG.
    def test_default_category_is_debug(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_print("test message")

            call_arg = mock_console.print.call_args[0][0]
            assert "[DEBUG]" in call_arg

    # * Verify delegates to output manager
    # * Delegates to get_output_manager().debug().
    def test_delegates_to_output_manager(self, isolate_config):
        mock_manager = MagicMock()
        set_output_manager(mock_manager)

        debug_print("test message", "CATEGORY")

        mock_manager.debug.assert_called_once_with("test message", "CATEGORY")
        reset_output_manager()

# * Tests for debug_ai() function

class TestDebugAi:

    # * Verify uses AI category
    # * debug_ai uses 'AI' as category.
    def test_uses_ai_category(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_ai("model response")

            call_arg = mock_console.print.call_args[0][0]
            assert "[AI]" in call_arg
            assert "model response" in call_arg

    # * Verify silent when debug disabled
    # * Does not print when debug level is not enabled.
    def test_silent_when_debug_disabled(self, normal_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_ai("model response")

            mock_console.print.assert_not_called()

    # * Verify delegates to output manager
    # * Delegates to get_output_manager().debug().
    def test_delegates_to_output_manager(self, isolate_config):
        mock_manager = MagicMock()
        set_output_manager(mock_manager)

        debug_ai("model response")

        mock_manager.debug.assert_called_once_with("model response", "AI")
        reset_output_manager()

# * Tests for debug_error() function

class TestDebugError:

    # * Verify formats exception
    # * Formats exception type & message.
    def test_formats_exception(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            error = ValueError("test error")
            debug_error(error)

            call_arg = mock_console.print.call_args[0][0]
            assert "ValueError" in call_arg
            assert "test error" in call_arg

    # * Verify includes context
    # * Includes context when provided.
    def test_includes_context(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            error = ValueError("test error")
            debug_error(error, "during parsing")

            call_arg = mock_console.print.call_args[0][0]
            assert "during parsing" in call_arg

    # * Verify uses ERROR category
    # * Uses ERROR as category.
    def test_uses_error_category(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_error(ValueError("test"))

            call_arg = mock_console.print.call_args[0][0]
            assert "[ERROR]" in call_arg

    # * Verify silent when debug disabled
    # * Does not print when debug level is not enabled.
    def test_silent_when_debug_disabled(self, normal_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_error(ValueError("test"))

            mock_console.print.assert_not_called()

# * Tests for debug_api_call() function

class TestDebugApiCall:

    # * Verify formats api call info
    # * Formats API call information.
    def test_formats_api_call_info(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_api_call("openai", "gpt-4o", 1000, 500)

            call_arg = mock_console.print.call_args[0][0]
            assert "openai" in call_arg
            assert "gpt-4o" in call_arg
            assert "1000" in call_arg
            assert "500" in call_arg

    # * Verify handles no response length
    # * Works without response length.
    def test_handles_no_response_length(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_api_call("anthropic", "claude-3", 2000)

            # Check that our call was made (may have other calls from setup)
            assert mock_console.print.called
            # Find our specific call in the call list
            call_args = [str(call) for call in mock_console.print.call_args_list]
            matching = [c for c in call_args if "anthropic" in c and "2000" in c]
            assert len(matching) == 1, f"Expected one matching call, got: {call_args}"

    # * Verify uses API category
    # * Uses API as category.
    def test_uses_api_category(self, debug_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_api_call("openai", "gpt-4o", 1000)

            call_arg = mock_console.print.call_args[0][0]
            assert "[API]" in call_arg

    # * Verify silent when debug disabled
    # * Does not print when debug level is not enabled.
    def test_silent_when_debug_disabled(self, normal_output_manager):
        with patch("src.loom_io.console.console") as mock_console:
            debug_api_call("openai", "gpt-4o", 1000)

            mock_console.print.assert_not_called()
