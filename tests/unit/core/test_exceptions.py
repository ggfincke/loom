# tests/unit/test_exceptions.py
# Unit tests for exception hierarchy & error handling decorator

from pathlib import Path

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
    TypstError,
    DevModeError,
    ATSError,
    ProviderError,
    RateLimitError,
    ModelNotFoundError,
    DocumentError,
    DocumentParseError,
    UnsupportedFormatError,
    SectionNotFoundError,
    TemplateError,
    TemplateNotFoundError,
    TemplateParseError,
    SettingsValidationError,
    MissingAPIKeyError,
    CacheError,
    CacheCorruptError,
    BulkProcessingError,
    JobDiscoveryError,
    RetryExhaustedError,
    FileOperationError,
    FileReadError,
    FileWriteError,
    format_error_message,
)
from src.cli.decorators import handle_loom_error

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
        # should have exactly one "[red]" & one "[/]"
        assert result.count("[red]") == 1
        assert result.count("[/]") == 1

    # * Test format_error_message w/ multiline message
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
            TypstError("typst error"),
            DevModeError("dev mode error"),
            ATSError("ats error"),
            # New Group G exceptions
            ProviderError("provider error", provider="openai"),
            RateLimitError("rate limit", provider="openai"),
            ModelNotFoundError("model not found"),
            DocumentError("document error"),
            DocumentParseError("parse error"),
            UnsupportedFormatError("unsupported", format=".xyz"),
            SectionNotFoundError("section not found", section_name="experience"),
            TemplateError("template error"),
            TemplateNotFoundError("template not found"),
            TemplateParseError("template parse error"),
            SettingsValidationError("invalid", setting_name="temp", value=5.0),
            MissingAPIKeyError(
                "missing key", provider="openai", env_var="OPENAI_API_KEY"
            ),
            CacheError("cache error"),
            CacheCorruptError("cache corrupt"),
            BulkProcessingError("bulk error"),
            JobDiscoveryError("job discovery error"),
            RetryExhaustedError("retry exhausted", job_id="job1", attempts=3),
            FileOperationError("file error", path="/tmp/test.txt"),
            FileReadError("read error", path="/tmp/test.txt"),
            FileWriteError("write error", path="/tmp/test.txt"),
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


# =============================================================================
# Group G: Expanded Exception Hierarchy Tests
# =============================================================================


# * Test new AI & Provider exceptions
class TestProviderExceptions:

    # * Test ProviderError has provider attribute
    def test_provider_error_has_provider_attribute(self):
        error = ProviderError("API failed", provider="openai")
        assert error.provider == "openai"
        assert isinstance(error, AIError)
        assert isinstance(error, LoomError)
        assert str(error) == "API failed"

    # * Test ProviderError __repr__
    def test_provider_error_repr(self):
        error = ProviderError("API failed", provider="openai")
        repr_str = repr(error)
        assert "ProviderError" in repr_str
        assert "'API failed'" in repr_str
        assert "provider='openai'" in repr_str

    # * Test RateLimitError has retry_after attribute
    def test_rate_limit_error_has_retry_after(self):
        error = RateLimitError("Rate limited", provider="openai", retry_after=60)
        assert error.retry_after == 60
        assert error.provider == "openai"
        assert isinstance(error, ProviderError)
        assert isinstance(error, AIError)

    # * Test RateLimitError w/ None retry_after
    def test_rate_limit_error_none_retry_after(self):
        error = RateLimitError("Rate limited", provider="anthropic")
        assert error.retry_after is None
        assert error.provider == "anthropic"

    # * Test RateLimitError __repr__
    def test_rate_limit_error_repr(self):
        error = RateLimitError("Rate limited", provider="openai", retry_after=60)
        repr_str = repr(error)
        assert "RateLimitError" in repr_str
        assert "provider='openai'" in repr_str
        assert "retry_after=60" in repr_str

    # * Test ModelNotFoundError inherits from AIError
    def test_model_not_found_error_inheritance(self):
        error = ModelNotFoundError("Model gpt-99 not found")
        assert isinstance(error, AIError)
        assert isinstance(error, LoomError)
        assert "gpt-99" in str(error)


# * Test new Document exceptions
class TestDocumentExceptions:

    # * Test DocumentError is base for document exceptions
    def test_document_error_base(self):
        error = DocumentError("document error")
        assert isinstance(error, LoomError)
        assert str(error) == "document error"

    # * Test DocumentParseError inheritance
    def test_document_parse_error_inheritance(self):
        error = DocumentParseError("Failed to parse DOCX")
        assert isinstance(error, DocumentError)
        assert isinstance(error, LoomError)

    # * Test UnsupportedFormatError has format attribute
    def test_unsupported_format_error_has_format(self):
        error = UnsupportedFormatError("Format not supported", format=".xyz")
        assert error.format == ".xyz"
        assert isinstance(error, DocumentError)

    # * Test UnsupportedFormatError __repr__
    def test_unsupported_format_error_repr(self):
        error = UnsupportedFormatError("Format not supported", format=".xyz")
        repr_str = repr(error)
        assert "UnsupportedFormatError" in repr_str
        assert "format='.xyz'" in repr_str

    # * Test SectionNotFoundError has section_name attribute
    def test_section_not_found_error_has_section_name(self):
        error = SectionNotFoundError("Section not found", section_name="experience")
        assert error.section_name == "experience"
        assert isinstance(error, DocumentError)

    # * Test SectionNotFoundError __repr__
    def test_section_not_found_error_repr(self):
        error = SectionNotFoundError("Section not found", section_name="experience")
        repr_str = repr(error)
        assert "SectionNotFoundError" in repr_str
        assert "section_name='experience'" in repr_str


# * Test new Template exceptions
class TestTemplateExceptions:

    # * Test TemplateError is base for template exceptions
    def test_template_error_base(self):
        error = TemplateError("template error")
        assert isinstance(error, LoomError)
        assert str(error) == "template error"

    # * Test TemplateNotFoundError inheritance
    def test_template_not_found_error_inheritance(self):
        error = TemplateNotFoundError(
            "Template descriptor not found: /path/to/template.toml"
        )
        assert isinstance(error, TemplateError)
        assert isinstance(error, LoomError)

    # * Test TemplateParseError inheritance
    def test_template_parse_error_inheritance(self):
        error = TemplateParseError("Invalid TOML in template")
        assert isinstance(error, TemplateError)
        assert isinstance(error, LoomError)


# * Test new Configuration exceptions
class TestConfigurationExceptions:

    # * Test SettingsValidationError has setting_name & value attributes
    def test_settings_validation_error_has_attributes(self):
        error = SettingsValidationError(
            "temperature must be 0.0-2.0",
            setting_name="temperature",
            value=5.0,
        )
        assert error.setting_name == "temperature"
        assert error.value == 5.0
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, LoomError)

    # * Test SettingsValidationError __repr__
    def test_settings_validation_error_repr(self):
        error = SettingsValidationError(
            "Invalid value",
            setting_name="temperature",
            value=5.0,
        )
        repr_str = repr(error)
        assert "SettingsValidationError" in repr_str
        assert "setting_name='temperature'" in repr_str
        assert "value=5.0" in repr_str

    # * Test MissingAPIKeyError has provider & env_var attributes
    def test_missing_api_key_error_has_attributes(self):
        error = MissingAPIKeyError(
            "OpenAI API key not found",
            provider="openai",
            env_var="OPENAI_API_KEY",
        )
        assert error.provider == "openai"
        assert error.env_var == "OPENAI_API_KEY"
        assert isinstance(error, ConfigurationError)

    # * Test MissingAPIKeyError __repr__
    def test_missing_api_key_error_repr(self):
        error = MissingAPIKeyError(
            "Missing key",
            provider="openai",
            env_var="OPENAI_API_KEY",
        )
        repr_str = repr(error)
        assert "MissingAPIKeyError" in repr_str
        assert "provider='openai'" in repr_str
        assert "env_var='OPENAI_API_KEY'" in repr_str


# * Test new Cache exceptions
class TestCacheExceptions:

    # * Test CacheError is base for cache exceptions
    def test_cache_error_base(self):
        error = CacheError("cache error")
        assert isinstance(error, LoomError)
        assert str(error) == "cache error"

    # * Test CacheCorruptError inheritance
    def test_cache_corrupt_error_inheritance(self):
        error = CacheCorruptError("Cache file corrupted")
        assert isinstance(error, CacheError)
        assert isinstance(error, LoomError)


# * Test new Bulk Processing exceptions
class TestBulkProcessingExceptions:

    # * Test BulkProcessingError is base for bulk processing exceptions
    def test_bulk_processing_error_base(self):
        error = BulkProcessingError("bulk error")
        assert isinstance(error, LoomError)
        assert str(error) == "bulk error"

    # * Test JobDiscoveryError inheritance
    def test_job_discovery_error_inheritance(self):
        error = JobDiscoveryError("No jobs found at /path/to/jobs")
        assert isinstance(error, BulkProcessingError)
        assert isinstance(error, LoomError)

    # * Test RetryExhaustedError has job_id & attempts attributes
    def test_retry_exhausted_error_has_attributes(self):
        error = RetryExhaustedError(
            "Max retries exceeded",
            job_id="job_123",
            attempts=3,
        )
        assert error.job_id == "job_123"
        assert error.attempts == 3
        assert isinstance(error, BulkProcessingError)

    # * Test RetryExhaustedError __repr__
    def test_retry_exhausted_error_repr(self):
        error = RetryExhaustedError(
            "Max retries exceeded",
            job_id="job_123",
            attempts=3,
        )
        repr_str = repr(error)
        assert "RetryExhaustedError" in repr_str
        assert "job_id='job_123'" in repr_str
        assert "attempts=3" in repr_str


# * Test new File I/O exceptions
class TestFileOperationExceptions:

    # * Test FileOperationError has path attribute
    def test_file_operation_error_has_path(self):
        error = FileOperationError("File error", path="/tmp/test.txt")
        assert error.path == Path("/tmp/test.txt")
        assert isinstance(error, LoomError)

    # * Test FileOperationError w/ Path object
    def test_file_operation_error_with_path_object(self):
        path = Path("/tmp/test.txt")
        error = FileOperationError("File error", path=path)
        assert error.path == path

    # * Test FileOperationError __repr__
    def test_file_operation_error_repr(self):
        error = FileOperationError("File error", path="/tmp/test.txt")
        repr_str = repr(error)
        assert "FileOperationError" in repr_str
        assert "path=" in repr_str

    # * Test FileReadError inheritance
    def test_file_read_error_inheritance(self):
        error = FileReadError("Cannot read file", path="/tmp/test.txt")
        assert isinstance(error, FileOperationError)
        assert isinstance(error, LoomError)
        assert error.path == Path("/tmp/test.txt")

    # * Test FileWriteError inheritance
    def test_file_write_error_inheritance(self):
        error = FileWriteError("Cannot write file", path="/tmp/test.txt")
        assert isinstance(error, FileOperationError)
        assert isinstance(error, LoomError)
        assert error.path == Path("/tmp/test.txt")


# * Test exception chaining patterns (from e)
class TestExceptionChaining:

    # * Test exception chain is preserved w/ from e
    def test_exception_chain_preserved(self):
        try:
            try:
                raise ValueError("original error")
            except ValueError as e:
                raise TemplateParseError("Template invalid") from e
        except TemplateParseError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "original error"

    # * Test multi-level chaining
    def test_multi_level_exception_chain(self):
        try:
            try:
                try:
                    raise FileNotFoundError("file.txt")
                except FileNotFoundError as e1:
                    raise FileReadError("Cannot read", path="/tmp/file.txt") from e1
            except FileReadError as e2:
                raise DocumentParseError("Failed to parse document") from e2
        except DocumentParseError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, FileReadError)
            assert e.__cause__.__cause__ is not None
            assert isinstance(e.__cause__.__cause__, FileNotFoundError)


# * Test handle_loom_error decorator w/ new exceptions
class TestDecoratorWithNewExceptions:

    @pytest.mark.parametrize(
        "exception_class,exception_args,expected_error_type",
        [
            (DocumentError, ("doc error",), "Document Error"),
            (DocumentParseError, ("parse error",), "Document Error"),
            (TemplateError, ("template error",), "Template Error"),
            (TemplateNotFoundError, ("not found",), "Template Error"),
            (TemplateParseError, ("parse error",), "Template Error"),
            (BulkProcessingError, ("bulk error",), "Bulk Processing Error"),
            (JobDiscoveryError, ("no jobs",), "Bulk Processing Error"),
            (CacheError, ("cache error",), "Cache Error"),
            (CacheCorruptError, ("corrupt",), "Cache Error"),
        ],
    )
    @patch("src.loom_io.console.console")
    # * Test new exception types are handled by decorator
    def test_new_exceptions_handled(
        self, mock_console, exception_class, exception_args, expected_error_type
    ):
        @handle_loom_error
        def function_with_new_exception():
            raise exception_class(*exception_args)

        with pytest.raises(SystemExit) as exc_info:
            function_with_new_exception()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_once()
        error_msg = mock_console.print.call_args[0][0]
        assert expected_error_type in error_msg

    @patch("src.loom_io.console.console")
    # * Test FileOperationError handled as File Error
    def test_file_operation_error_handled(self, mock_console):
        @handle_loom_error
        def function_with_file_error():
            raise FileReadError("Cannot read", path="/tmp/test.txt")

        with pytest.raises(SystemExit) as exc_info:
            function_with_file_error()

        assert exc_info.value.code == 1
        error_msg = mock_console.print.call_args[0][0]
        assert "File Error" in error_msg

    @patch("src.loom_io.console.console")
    # * Test RetryExhaustedError handled as Bulk Processing Error
    def test_retry_exhausted_error_handled(self, mock_console):
        @handle_loom_error
        def function_with_retry_error():
            raise RetryExhaustedError("Max retries", job_id="job1", attempts=3)

        with pytest.raises(SystemExit) as exc_info:
            function_with_retry_error()

        assert exc_info.value.code == 1
        error_msg = mock_console.print.call_args[0][0]
        assert "Bulk Processing Error" in error_msg

    @patch("src.loom_io.console.console")
    # * Test SettingsValidationError handled as Configuration Error
    def test_settings_validation_error_handled(self, mock_console):
        @handle_loom_error
        def function_with_settings_error():
            raise SettingsValidationError("Invalid", setting_name="temp", value=5.0)

        with pytest.raises(SystemExit) as exc_info:
            function_with_settings_error()

        assert exc_info.value.code == 1
        error_msg = mock_console.print.call_args[0][0]
        assert "Configuration Error" in error_msg

    @patch("src.loom_io.console.console")
    # * Test ProviderError handled as AI Error
    def test_provider_error_handled(self, mock_console):
        @handle_loom_error
        def function_with_provider_error():
            raise ProviderError("API failed", provider="openai")

        with pytest.raises(SystemExit) as exc_info:
            function_with_provider_error()

        assert exc_info.value.code == 1
        error_msg = mock_console.print.call_args[0][0]
        assert "AI Error" in error_msg
