# src/cli/decorators.py
# CLI decorators for error handling, access control, & watch mode support

import functools
from pathlib import Path
from typing import Callable, TypeVar, Any, cast

import typer

from ..core.exceptions import (
    LoomError,
    ValidationError,
    JSONParsingError,
    AIError,
    EditError,
    ConfigurationError,
    LaTeXError,
    TypstError,
    DevModeError,
    ATSError,
    DocumentError,
    TemplateError,
    BulkProcessingError,
    FileOperationError,
    CacheError,
    format_error_message,
)

F = TypeVar("F", bound=Callable[..., Any])


# * Decorator for handling Loom errors in CLI commands w/ Rich output
def handle_loom_error(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # ! Lazy import to avoid circular dependencies
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
        except DocumentError as e:
            console.print(format_error_message("Document Error", str(e)))
            raise SystemExit(1)
        except TemplateError as e:
            console.print(format_error_message("Template Error", str(e)))
            raise SystemExit(1)
        except BulkProcessingError as e:
            console.print(format_error_message("Bulk Processing Error", str(e)))
            raise SystemExit(1)
        except FileOperationError as e:
            console.print(format_error_message("File Error", str(e)))
            raise SystemExit(1)
        except CacheError as e:
            console.print(format_error_message("Cache Error", str(e)))
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


# * Wrap command execution w/ watch mode support
def run_with_watch(
    paths: list[Path | None],
    run_func: Callable[[], None],
    debounce: float = 1.0,
) -> None:
    from .watch import WatchRunner

    valid_paths = [p for p in paths if p is not None]
    runner = WatchRunner(valid_paths, run_func, debounce)
    runner.start()
