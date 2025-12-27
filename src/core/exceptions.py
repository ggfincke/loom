# src/core/exceptions.py
# Custom exception hierarchy & centralized error handling for Loom

import functools
from typing import List, Callable, TypeVar, Any, cast
import typer

# type var for decorator typing
F = TypeVar("F", bound=Callable[..., Any])


# * Format error message for display (pure string formatting, no I/O)
def format_error_message(error_type: str, message: str) -> str:
    # Format error message w/ consistent Rich markup styling.
    return f"[red]{error_type}:[/] {message}"


# * Base exception for Loom application
class LoomError(Exception):
    pass


# * Validation-specific error for handling warnings & recoverable errors w/ context
class ValidationError(LoomError):
    def __init__(self, warnings: List[str], recoverable: bool = True):
        self.warnings = warnings
        self.recoverable = recoverable
        # include warning details in message for clearer error context
        details = "; ".join(warnings) if warnings else "no details"
        message = f"Validation failed with {len(warnings)} warnings: {details}"
        super().__init__(message)


# * AI-related exceptions
class AIError(LoomError):
    pass


# * Edit application errors
class EditError(LoomError):
    pass


# * Configuration errors
class ConfigurationError(LoomError):
    pass


# * JSON parsing errors
class JSONParsingError(LoomError):
    pass


# * LaTeX-specific errors
class LaTeXError(LoomError):
    pass


# * Typst-specific errors
class TypstError(LoomError):
    pass


# * Dev mode access control errors
class DevModeError(LoomError):
    pass


# * ATS compatibility check errors
class ATSError(LoomError):
    pass


# * Decorator for handling Loom errors in CLI commands
# ? Pragmatic exception: This decorator needs console output for error display.
# ? Lazy import pattern used to avoid circular dependencies while keeping
# ? error handling centralized in the core layer.
# todo: Move this decorator to cli/ layer to honor "core is pure (no I/O)" rule.
# todo: The I/O (console.print + SystemExit) belongs at the CLI boundary, not core.
def handle_loom_error(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from ..loom_io.console import console

        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            if not e.recoverable:
                console.print(format_error_message("Validation Error", str(e)))
                raise SystemExit(1)
            # allow function to continue for recoverable errors
            return None
        except JSONParsingError as e:
            console.print(format_error_message("JSON Parsing Error", str(e)))
            raise SystemExit(1)
        except AIError as e:
            console.print(format_error_message("AI Error", str(e)))
            raise SystemExit(1)
        except EditError as e:
            console.print(format_error_message("Edit Error", str(e)))
            raise SystemExit(1)
        except ConfigurationError as e:
            console.print(format_error_message("Configuration Error", str(e)))
            raise SystemExit(1)
        except LaTeXError as e:
            console.print(format_error_message("LaTeX Error", str(e)))
            raise SystemExit(1)
        except TypstError as e:
            console.print(format_error_message("Typst Error", str(e)))
            raise SystemExit(1)
        except DevModeError as e:
            console.print(format_error_message("Dev Mode Error", str(e)))
            raise SystemExit(1)
        except ATSError as e:
            console.print(format_error_message("ATS Error", str(e)))
            raise SystemExit(1)
        except LoomError as e:
            console.print(format_error_message("Error", str(e)))
            raise SystemExit(1)
        except Exception as e:
            console.print(format_error_message("Unexpected Error", str(e)))
            raise SystemExit(1)

    return cast(F, wrapper)


# * Decorator to require dev mode for development commands
def require_dev_mode(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # ! Lazy import to avoid circular dependencies
        from ..config.dev_mode import is_dev_mode_enabled

        # extract ctx from args (first positional arg is always typer.Context)
        ctx = args[0] if args and isinstance(args[0], typer.Context) else None

        # use unified dev mode check w/ ctx for test injection support
        if not is_dev_mode_enabled(ctx):
            raise DevModeError(
                "Development mode required. Enable with: loom config set dev_mode true"
            )

        return func(*args, **kwargs)

    return cast(F, wrapper)
