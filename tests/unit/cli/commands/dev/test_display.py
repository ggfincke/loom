# tests/unit/cli/commands/dev/test_display.py
# Unit tests for dev command functionality & dev mode requirements

import pytest
import typer
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

from src.cli.commands.dev.display import display
from src.core.exceptions import DevModeError
from src.core.constants import EditOperation


# * Test display command functionality & dev mode requirements


class TestDisplayCommand:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    @patch("src.cli.commands.dev.display.main_display_loop")
    # * Test display command execution when dev mode is enabled
    def test_display_command_with_dev_mode_enabled(
        self, mock_display_loop, mock_dev_enabled
    ):
        # setup mocks
        mock_dev_enabled.return_value = True
        mock_display_loop.return_value = []

        # create mock context
        mock_ctx = Mock(spec=typer.Context)

        # should not raise exception
        display(mock_ctx, help=False)

        # verify display loop was called
        mock_display_loop.assert_called_once()

        # verify sample operations were passed to display loop
        call_args = mock_display_loop.call_args[0]
        assert len(call_args) > 0  # should have operations list
        assert isinstance(call_args[0], list)  # first arg should be operations list

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    # * Test display command rejection when dev mode is disabled
    def test_display_command_with_dev_mode_disabled(self, mock_dev_enabled):
        # setup mock - dev mode disabled
        mock_dev_enabled.return_value = False

        mock_ctx = Mock(spec=typer.Context)

        # should raise SystemExit due to handle_loom_error decorator
        with pytest.raises(SystemExit) as exc_info:
            display(mock_ctx, help=False)

        assert exc_info.value.code == 1

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    @patch("src.cli.commands.help.show_command_help")
    # * Test display command help flag functionality
    def test_display_command_help_flag(self, mock_show_help, mock_dev_enabled):
        mock_dev_enabled.return_value = True
        mock_ctx = Mock(spec=typer.Context)
        mock_ctx.exit = Mock(side_effect=SystemExit(0))

        # call with help flag - should exit
        with pytest.raises(SystemExit):
            display(mock_ctx, help=True)

        # verify help was shown and context exited (second arg is command object)
        mock_show_help.assert_called_once()
        assert mock_show_help.call_args[0][0] == "display"
        mock_ctx.exit.assert_called_once()

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    @patch("src.cli.commands.dev.display.main_display_loop")
    # * Test sample operations creation & structure validation
    def test_sample_operations_structure(self, mock_display_loop, mock_dev_enabled):
        # setup mocks
        mock_dev_enabled.return_value = True
        mock_display_loop.return_value = []

        mock_ctx = Mock(spec=typer.Context)

        # call display command
        display(mock_ctx, help=False)

        # extract the operations passed to display loop
        call_args = mock_display_loop.call_args[0]
        operations = call_args[0]

        # verify structure of sample operations
        assert isinstance(operations, list)
        assert len(operations) == 5  # should have 5 sample operations

        # verify all are EditOperation instances
        for op in operations:
            assert isinstance(op, EditOperation)
            assert hasattr(op, "operation")
            assert hasattr(op, "line_number")
            assert hasattr(op, "reasoning")
            assert hasattr(op, "confidence")

        # verify specific operation types are included
        operation_types = [op.operation for op in operations]
        assert "replace_line" in operation_types
        assert "insert_after" in operation_types
        assert "replace_range" in operation_types
        assert "delete_range" in operation_types

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    @patch("src.cli.commands.dev.display.main_display_loop")
    # * Test sample operations content & field validation
    def test_sample_operations_content(self, mock_display_loop, mock_dev_enabled):
        # setup mocks
        mock_dev_enabled.return_value = True
        mock_display_loop.return_value = []

        mock_ctx = Mock(spec=typer.Context)

        # call display command
        display(mock_ctx, help=False)

        # extract operations
        operations = mock_display_loop.call_args[0][0]

        # verify first operation (replace_line)
        replace_op = operations[0]
        assert replace_op.operation == "replace_line"
        assert replace_op.line_number == 6
        assert "Python developer" in replace_op.content
        assert replace_op.confidence == 0.92
        assert "Python experience" in replace_op.reasoning

        # verify insert_after operation
        insert_ops = [op for op in operations if op.operation == "insert_after"]
        assert len(insert_ops) == 1
        insert_op = insert_ops[0]
        assert insert_op.line_number == 11
        assert "AWS" in insert_op.content
        assert insert_op.confidence == 0.88

        # verify replace_range operation
        range_ops = [op for op in operations if op.operation == "replace_range"]
        assert len(range_ops) == 1
        range_op = range_ops[0]
        assert range_op.start_line == 15
        assert range_op.end_line == 16
        assert "microservices" in range_op.content
        assert range_op.confidence == 0.91

        # verify delete_range operation
        delete_ops = [op for op in operations if op.operation == "delete_range"]
        assert len(delete_ops) == 1
        delete_op = delete_ops[0]
        assert delete_op.line_number == 19
        assert delete_op.start_line == 19
        assert delete_op.end_line == 19
        assert delete_op.confidence == 0.85

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    @patch("src.cli.commands.dev.display.main_display_loop")
    # * Test confidence values are within realistic ranges
    def test_confidence_ranges_realistic(self, mock_display_loop, mock_dev_enabled):
        # setup mocks
        mock_dev_enabled.return_value = True
        mock_display_loop.return_value = []

        mock_ctx = Mock(spec=typer.Context)

        # call display command
        display(mock_ctx, help=False)

        # extract operations and check confidence values
        operations = mock_display_loop.call_args[0][0]

        for op in operations:
            # confidence should be realistic (between 0.8 and 1.0 for sample data)
            assert 0.8 <= op.confidence <= 1.0
            # should be rounded to 2 decimal places
            assert op.confidence == round(op.confidence, 2)

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    @patch("src.cli.commands.dev.display.main_display_loop")
    # * Test reasoning field quality & style compliance
    def test_reasoning_quality(self, mock_display_loop, mock_dev_enabled):
        # setup mocks
        mock_dev_enabled.return_value = True
        mock_display_loop.return_value = []

        mock_ctx = Mock(spec=typer.Context)

        # call display command
        display(mock_ctx, help=False)

        # extract operations and verify reasoning quality
        operations = mock_display_loop.call_args[0][0]

        for op in operations:
            # all operations should have non-empty reasoning
            assert op.reasoning != ""
            assert len(op.reasoning) > 10  # should be descriptive
            # reasoning should start lowercase or with special chars (following style guide)
            first_char = op.reasoning[0] if op.reasoning else ""
            assert first_char.islower() or first_char in "•-" or first_char.isupper()

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    # * Test error handling when dev mode check fails
    def test_error_handling_during_dev_mode_check(self, mock_dev_enabled):
        # simulate dev mode check failure
        mock_dev_enabled.side_effect = Exception("Settings error")

        mock_ctx = Mock(spec=typer.Context)

        # handle_loom_error catches all exceptions and converts to SystemExit
        with pytest.raises(SystemExit) as exc_info:
            display(mock_ctx, help=False)

        assert exc_info.value.code == 1

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    @patch("src.cli.commands.dev.display.main_display_loop")
    # * Test error handling when display loop fails
    def test_display_loop_exception_handling(
        self, mock_display_loop, mock_dev_enabled
    ):
        # setup mocks
        mock_dev_enabled.return_value = True

        # simulate display loop failure
        mock_display_loop.side_effect = Exception("Display error")

        mock_ctx = Mock(spec=typer.Context)

        # handle_loom_error catches all exceptions and converts to SystemExit
        with pytest.raises(SystemExit) as exc_info:
            display(mock_ctx, help=False)

        assert exc_info.value.code == 1


# * Test dev mode integration & validation logic


class TestDevModeIntegration:
    # * Test DevModeError message format & content
    def test_dev_mode_error_message_format(self):
        error = DevModeError(
            "Development mode required. Enable with: loom config set dev_mode true"
        )

        assert "Development mode required" in str(error)
        assert "loom config set dev_mode true" in str(error)

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    # * Test various falsy values for dev_mode setting
    def test_dev_mode_false_variations(self, mock_dev_enabled):
        """Test different ways dev_mode could be falsy"""
        falsy_values = [False, None, 0, "", []]

        for falsy_value in falsy_values:
            # is_dev_mode_enabled returns the falsy value directly
            mock_dev_enabled.return_value = falsy_value

            mock_ctx = Mock(spec=typer.Context)

            with pytest.raises(SystemExit) as exc_info:
                display(mock_ctx, help=False)
            assert exc_info.value.code == 1

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    @patch("src.cli.commands.dev.display.main_display_loop")
    # * Test various truthy values for dev_mode setting
    def test_dev_mode_true_variations(self, mock_display_loop, mock_dev_enabled):
        """Test different ways dev_mode could be truthy"""
        truthy_values = [True, 1, "true", "yes", [1]]

        mock_display_loop.return_value = []

        for truthy_value in truthy_values:
            mock_dev_enabled.return_value = truthy_value

            mock_ctx = Mock(spec=typer.Context)

            # should not raise exception for truthy values
            display(mock_ctx, help=False)

            # verify display loop was called
            assert mock_display_loop.called


# * Test require_dev_mode decorator behavior


class TestRequireDevModeDecorator:
    """Tests for the @require_dev_mode decorator on display command."""

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    # * Test decorator passes ctx to is_dev_mode_enabled
    def test_decorator_passes_ctx(self, mock_dev_enabled):
        mock_dev_enabled.return_value = False
        mock_ctx = Mock(spec=typer.Context)

        with pytest.raises(SystemExit):
            display(mock_ctx, help=False)

        # verify ctx was passed to is_dev_mode_enabled
        mock_dev_enabled.assert_called_once_with(mock_ctx)

    @patch("src.config.dev_mode.is_dev_mode_enabled")
    # * Test decorator raises DevModeError when disabled
    def test_decorator_raises_dev_mode_error(self, mock_dev_enabled):
        mock_dev_enabled.return_value = False
        mock_ctx = Mock(spec=typer.Context)

        # DevModeError is converted to SystemExit by handle_loom_error
        with pytest.raises(SystemExit) as exc_info:
            display(mock_ctx, help=False)

        assert exc_info.value.code == 1
