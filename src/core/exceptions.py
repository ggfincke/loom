# src/core/exceptions.py
# Custom exception hierarchy for Loom (pure - no I/O operations)

from pathlib import Path
from typing import List, Any


# * Format error message for display (pure string formatting, no I/O)
def format_error_message(error_type: str, message: str) -> str:
    return f"[red]{error_type}:[/] {message}"


# * Base exception for Loom application
class LoomError(Exception):
    pass


# * Validation-specific error for handling warnings & recoverable errors w/ context
class ValidationError(LoomError):
    def __init__(self, warnings: List[str], recoverable: bool = True):
        self.warnings = warnings
        self.recoverable = recoverable
        details = "; ".join(warnings) if warnings else "no details"
        message = f"Validation failed with {len(warnings)} warnings: {details}"
        super().__init__(message)


# * Edit operation validation failed (e.g., invalid line numbers, conflicts)
class EditValidationError(ValidationError):
    pass


# * AI-related exceptions
class AIError(LoomError):
    pass


# * Provider-specific error (API errors, rate limits)
class ProviderError(AIError):
    def __init__(self, message: str, provider: str):
        super().__init__(message)
        self.provider = provider

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.args[0]!r}, provider={self.provider!r})"
        )


# * API rate limit exceeded
class RateLimitError(ProviderError):
    def __init__(self, message: str, provider: str, retry_after: int | None = None):
        super().__init__(message, provider)
        self.retry_after = retry_after

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.args[0]!r}, "
            f"provider={self.provider!r}, retry_after={self.retry_after!r})"
        )


# * Requested model not found or unsupported
class ModelNotFoundError(AIError):
    pass


# * Edit application errors
class EditError(LoomError):
    pass


# * Configuration errors
class ConfigurationError(LoomError):
    pass


# * Settings value validation failed
class SettingsValidationError(ConfigurationError):
    def __init__(self, message: str, setting_name: str, value: Any):
        super().__init__(message)
        self.setting_name = setting_name
        self.value = value

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.args[0]!r}, "
            f"setting_name={self.setting_name!r}, value={self.value!r})"
        )


# * Required API key not found
class MissingAPIKeyError(ConfigurationError):
    def __init__(self, message: str, provider: str, env_var: str):
        super().__init__(message)
        self.provider = provider
        self.env_var = env_var

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.args[0]!r}, "
            f"provider={self.provider!r}, env_var={self.env_var!r})"
        )


# * JSON parsing errors
class JSONParsingError(LoomError):
    pass


# * Base error for document processing
class DocumentError(LoomError):
    pass


# * Failed to parse document structure
class DocumentParseError(DocumentError):
    pass


# * Document format not supported
class UnsupportedFormatError(DocumentError):
    def __init__(self, message: str, format: str):
        super().__init__(message)
        self.format = format

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.args[0]!r}, format={self.format!r})"


# * Requested section not found in document
class SectionNotFoundError(DocumentError):
    def __init__(self, message: str, section_name: str):
        super().__init__(message)
        self.section_name = section_name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.args[0]!r}, section_name={self.section_name!r})"


# * LaTeX-specific errors
class LaTeXError(LoomError):
    pass


# * Typst-specific errors
class TypstError(LoomError):
    pass


# * Base error for template loading & validation
class TemplateError(LoomError):
    pass


# * Template descriptor not found
class TemplateNotFoundError(TemplateError):
    pass


# * Template descriptor parsing failed
class TemplateParseError(TemplateError):
    pass


# * Base error for cache operations
class CacheError(LoomError):
    pass


# * Cache data corrupted
class CacheCorruptError(CacheError):
    pass


# * Base error for bulk processing
class BulkProcessingError(LoomError):
    pass


# * Failed to discover jobs
class JobDiscoveryError(BulkProcessingError):
    pass


# * Max retries exceeded for operation
class RetryExhaustedError(BulkProcessingError):
    def __init__(self, message: str, job_id: str, attempts: int):
        super().__init__(message)
        self.job_id = job_id
        self.attempts = attempts

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.args[0]!r}, "
            f"job_id={self.job_id!r}, attempts={self.attempts!r})"
        )


# * Base error for file I/O operations
class FileOperationError(LoomError):
    def __init__(self, message: str, path: Path | str):
        super().__init__(message)
        self.path = Path(path) if isinstance(path, str) else path

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.args[0]!r}, path={self.path!r})"


# * Failed to read file
class FileReadError(FileOperationError):
    pass


# * Failed to write file
class FileWriteError(FileOperationError):
    pass


# * Dev mode access control errors
class DevModeError(LoomError):
    pass


# * ATS compatibility check errors
class ATSError(LoomError):
    pass
