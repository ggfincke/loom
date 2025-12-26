# tests/unit/test_exceptions.py
# Unit tests for exception hierarchy & error handling decorator

import pytest
import typer
from unittest.mock import patch, MagicMock
from src.core.exceptions import (
    LoomError,
    ValidationError,
    AIError,
    EditError,
    ConfigurationError,
    JSONParsingError,
    LaTeXError,
    handle_loom_error,
    format_error_message,
)

# * Test format_error_message helper


class TestFormatErrorMessage:

    # * Test format_error_message produces correct Rich markup
    def test_format_error_message_basic(self):
        result = format_error_message("Test Error", "something went wrong")
        assert result == "[red]Test Error:[/] something went wrong"

    # * Test format_error_message handles empty message
    def test_format_error_message_empty(self):
        result = format_error_message("Error", "")
        assert result == "[red]Error:[/] "

    # * Test format_error_message preserves special characters
    def test_format_error_message_special_chars(self):
        result = format_error_message("JSON Error", "unexpected token at line 5: '{'")
        assert "unexpected token" in result
        assert "[red]JSON Error:[/]" in result

    # * Test format_error_message no duplicate prefixes
    def test_format_error_message_no_duplicate_prefix(self):
        result = format_error_message("AI Error", "model failed")
        # should have exactly one "[red]" and one "[/]"
        assert result.count("[red]") == 1
        assert result.count("[/]") == 1

    # * Test format_error_message with multiline message
    def test_format_error_message_multiline(self):
        result = format_error_message("Validation Error", "line 1\nline 2\nline 3")
        assert "[red]Validation Error:[/]" in result
        assert "line 1\nline 2\nline 3" in result


# * Test exception hierarchy & attributes


class TestExceptionHierarchy:

    # * Test LoomError is base exception class
    def test_loom_error_base_class(self):
        error = LoomError("test message")
        assert isinstance(error, Exception)
        assert str(error) == "test message"

    # * Test all custom exceptions inherit from LoomError
    def test_all_exceptions_inherit_from_loom_error(self):
        exceptions = [
            ValidationError(["warning"]),
            AIError("ai error"),
            EditError("edit error"),
            ConfigurationError("config error"),
            JSONParsingError("json error"),
            LaTeXError("latex error"),
        ]

        for exc in exceptions:
            assert isinstance(exc, LoomError)
            assert isinstance(exc, Exception)

    # * Test ValidationError has warnings & recoverable attributes
    def test_validation_error_attributes(self):
        warnings = ["warning 1", "warning 2"]

        # test default recoverable=True
        error = ValidationError(warnings)
        assert error.warnings == warnings
        assert error.recoverable is True
        assert "2 warnings" in str(error)

        # test explicit recoverable=False
        error_non_recoverable = ValidationError(warnings, recoverable=False)
        assert error_non_recoverable.warnings == warnings
        assert error_non_recoverable.recoverable is False

    # * Test ValidationError message formatting
    def test_validation_error_message_format(self):
        single_warning = ValidationError(["single"])
        assert "1 warnings" in str(single_warning)

        multiple_warnings = ValidationError(["first", "second", "third"])
        assert "3 warnings" in str(multiple_warnings)

        empty_warnings = ValidationError([])
        assert "0 warnings" in str(empty_warnings)


# * Test error handling decorator


class TestHandleLoomErrorDecorator:

    # * Test decorator allows successful function execution
    def test_successful_function_execution(self):
        @handle_loom_error
        def successful_function(x, y):
            return x + y

        result = successful_function(2, 3)
        assert result == 5

    @patch("src.loom_io.console.console")
    # * Test recoverable ValidationError returns None
    def test_validation_error_recoverable(self, mock_console):
        @handle_loom_error
        def function_with_recoverable_validation_error():
            raise ValidationError(["test warning"], recoverable=True)

        result = function_with_recoverable_validation_error()
        assert result is None
        # recoverable validation errors don't print & don't exit
        mock_console.print.assert_not_called()

    @patch("src.loom_io.console.console")
    # * Test non-recoverable ValidationError exits w/ code 1
    def test_validation_error_non_recoverable(self, mock_console):
        @handle_loom_error
        def function_with_non_recoverable_validation_error():
            raise ValidationError(["test warning"], recoverable=False)

        with pytest.raises(SystemExit) as exc_info:
            function_with_non_recoverable_validation_error()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_once()
        error_msg = mock_console.print.call_args[0][0]
        assert "Validation Error" in error_msg

    @pytest.mark.parametrize(
        "exception_class,expected_error_type",
        [
            (JSONParsingError, "JSON Parsing Error"),
            (AIError, "AI Error"),
            (EditError, "Edit Error"),
            (ConfigurationError, "Configuration Error"),
            (LaTeXError, "LaTeX Error"),
        ],
    )
    @patch("src.loom_io.console.console")
    # * Test specific LoomError subclasses exit w/ code 1 & proper formatting
    def test_specific_loom_errors(
        self, mock_console, exception_class, expected_error_type
    ):
        @handle_loom_error
        def function_with_specific_error():
            raise exception_class("specific error message")

        with pytest.raises(SystemExit) as exc_info:
            function_with_specific_error()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_once()
        error_msg = mock_console.print.call_args[0][0]
        assert expected_error_type in error_msg
        assert "specific error message" in error_msg

    @patch("src.loom_io.console.console")
    # * Test generic LoomError exits w/ code 1 & generic formatting
    def test_generic_loom_error(self, mock_console):
        @handle_loom_error
        def function_with_generic_loom_error():
            raise LoomError("generic loom error")

        with pytest.raises(SystemExit) as exc_info:
            function_with_generic_loom_error()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_once()
        error_msg = mock_console.print.call_args[0][0]
        assert "Error:" in error_msg
        assert "generic loom error" in error_msg

    @patch("src.loom_io.console.console")
    # * Test unexpected (non-Loom) exceptions exit w/ code 1
    def test_unexpected_exception(self, mock_console):
        @handle_loom_error
        def function_with_unexpected_error():
            raise ValueError("unexpected error")

        with pytest.raises(SystemExit) as exc_info:
            function_with_unexpected_error()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_once()
        error_msg = mock_console.print.call_args[0][0]
        assert "Unexpected Error:" in error_msg
        assert "unexpected error" in error_msg

    # * Test decorator preserves original function metadata
    def test_decorator_preserves_function_metadata(self):
        @handle_loom_error
        def documented_function(arg1, arg2=None):
            """This function has documentation."""
            return arg1

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This function has documentation."

    @patch("src.loom_io.console.console")
    # * Test decorator works w/ functions that have args & kwargs
    def test_function_with_args_and_kwargs(self, mock_console):
        @handle_loom_error
        def function_with_args(*args, **kwargs):
            if kwargs.get("should_error"):
                raise EditError("test error")
            return sum(args)

        # test successful execution w/ args
        result = function_with_args(1, 2, 3, should_error=False)
        assert result == 6

        # test error handling w/ kwargs
        with pytest.raises(SystemExit):
            function_with_args(1, 2, should_error=True)

    @patch("src.loom_io.console.console")
    # * Test decorator handles nested exception scenarios
    def test_nested_exceptions(self, mock_console):
        @handle_loom_error
        def function_with_nested_exception():
            try:
                raise ValueError("original error")
            except ValueError:
                raise AIError("wrapped in AI error")

        with pytest.raises(SystemExit) as exc_info:
            function_with_nested_exception()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_once()
        error_msg = mock_console.print.call_args[0][0]
        assert "AI Error:" in error_msg
        assert "wrapped in AI error" in error_msg


# * Test exception context & usage patterns


class TestExceptionUsage:

    # * Test ValidationError w/ empty warnings list
    def test_validation_error_empty_warnings(self):
        error = ValidationError([])
        assert error.warnings == []
        assert error.recoverable is True
        assert "0 warnings" in str(error)

    # * Test ValidationError w/ single warning
    def test_validation_error_single_warning(self):
        error = ValidationError(["single warning"])
        assert len(error.warnings) == 1
        assert error.warnings[0] == "single warning"

    # * Test ValidationError w/ multiple warnings
    def test_validation_error_multiple_warnings(self):
        warnings = [
            "Line 5 is out of bounds",
            "Operation missing required field 'text'",
            "Duplicate operation on line 3",
        ]
        error = ValidationError(warnings, recoverable=False)
        assert error.warnings == warnings
        assert not error.recoverable
        assert "3 warnings" in str(error)

    # * Test AIError preserves detailed messages
    def test_ai_error_message_preservation(self):
        detailed_message = (
            "AI model 'gpt-5' failed to generate valid JSON: unexpected token at line 5"
        )
        error = AIError(detailed_message)
        assert str(error) == detailed_message
        assert isinstance(error, LoomError)

    # * Test EditError w/ operation context
    def test_edit_error_operation_context(self):
        error = EditError("Cannot replace line 99: line does not exist")
        assert "line 99" in str(error)
        assert "does not exist" in str(error)

    # * Test JSONParsingError w/ code snippet context
    def test_json_parsing_error_with_snippet(self):
        error_msg = (
            'Invalid JSON syntax:\n{"incomplete": \nError: Expected closing brace'
        )
        error = JSONParsingError(error_msg)
        assert "Invalid JSON" in str(error)
        assert "incomplete" in str(error)

    # * Test ConfigurationError w/ settings context
    def test_configuration_error_settings_context(self):
        error = ConfigurationError("Invalid model setting: 'gpt-unknown' not supported")
        assert "Invalid model" in str(error)
        assert "gpt-unknown" in str(error)

    # * Test LaTeXError w/ compilation context
    def test_latex_error_compilation_context(self):
        error = LaTeXError("Compilation failed: \\usepackage{unknown} not found")
        assert "Compilation failed" in str(error)
        assert "usepackage" in str(error)


# * Test error scenarios & edge cases


class TestErrorEdgeCases:

    # * Test exception chaining behavior
    def test_exception_chaining(self):
        try:
            try:
                raise ValueError("original")
            except ValueError as e:
                raise EditError("chained error") from e
        except EditError as final_error:
            assert str(final_error) == "chained error"
            assert isinstance(final_error.__cause__, ValueError)

    # * Test exceptions w/ None or empty messages
    def test_exception_with_none_message(self):
        error = EditError("")
        assert str(error) == ""

        error2 = AIError(None)
        assert str(error2) == "None"

    @patch("src.loom_io.console.console")
    # * Test decorator handles exceptions raised in except blocks
    def test_decorator_with_exception_in_except_block(self, mock_console):
        @handle_loom_error
        def function_with_exception_in_except():
            try:
                raise ValueError("first error")
            except ValueError:
                raise JSONParsingError("error while handling error")

        with pytest.raises(SystemExit) as exc_info:
            function_with_exception_in_except()

        assert exc_info.value.code == 1
        error_msg = mock_console.print.call_args[0][0]
        assert "JSON Parsing Error:" in error_msg
        assert "error while handling error" in error_msg
