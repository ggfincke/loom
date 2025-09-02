# src/core/exceptions.py
# Custom exception hierarchy & centralized error handling for Loom

import functools
from typing import List, Callable, TypeVar, Any, cast
import typer

# type var for decorator typing
F = TypeVar('F', bound=Callable[..., Any])

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

# * Dev mode access control errors
class DevModeError(LoomError):
    pass


# * Decorator for handling Loom errors in CLI commands
def handle_loom_error(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # ! Lazy import to avoid circular dependencies  
        from ..loom_io.console import console
        
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            if not e.recoverable:
                console.print(f"[red]Validation Error:[/] {str(e)}")
                raise SystemExit(1)
            # allow function to continue for recoverable errors
            return None
        except JSONParsingError as e:
            console.print(f"[red]JSON Parsing Error:[/] {str(e)}")
            raise SystemExit(1)
        except AIError as e:
            console.print(f"[red]AI Error:[/] {str(e)}")
            raise SystemExit(1)
        except EditError as e:
            console.print(f"[red]Edit Error:[/] {str(e)}")
            raise SystemExit(1)
        except ConfigurationError as e:
            console.print(f"[red]Configuration Error:[/] {str(e)}")
            raise SystemExit(1)
        except LaTeXError as e:
            console.print(f"[red]LaTeX Error:[/] {str(e)}")
            raise SystemExit(1)
        except DevModeError as e:
            console.print(f"[red]Dev Mode Error:[/] {str(e)}")
            raise SystemExit(1)
        except LoomError as e:
            console.print(f"[red]Error:[/] {str(e)}")
            raise SystemExit(1)
        except Exception as e:
            console.print(f"[red]Unexpected Error:[/] {str(e)}")
            raise SystemExit(1)
    return cast(F, wrapper)


# * Decorator to require dev mode for development commands
def require_dev_mode(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # ! Lazy import to avoid circular dependencies
        from ..config.settings import get_settings
        
        # extract ctx from args (first positional arg is always typer.Context)
        ctx = args[0] if args and isinstance(args[0], typer.Context) else None
        if ctx is None:
            raise DevModeError("Cannot access development commands: missing context")
        
        # check if dev_mode is enabled
        settings = get_settings(ctx)
        if not settings.dev_mode:
            raise DevModeError(
                "Development mode required. Enable with: loom config set dev_mode true"
            )
        
        return func(*args, **kwargs)
    return cast(F, wrapper)
