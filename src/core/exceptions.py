# src/core/exceptions.py
# Custom exception hierarchy & centralized error handling for Loom

import functools
from typing import List
import typer

# * Base exception for Loom application
class LoomError(Exception):
    pass

# * Validation-specific error for handling warnings & recoverable errors w/ context
class ValidationError(LoomError):    
    def __init__(self, warnings: List[str], recoverable: bool = True):
        self.warnings = warnings
        self.recoverable = recoverable
        message = f"Validation failed with {len(warnings)} warnings"
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


# * Decorator for handling Loom errors in CLI commands
def handle_loom_error(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # ! Lazy import to avoid circular dependencies  
        from ..loom_io.console import console
        
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            if not e.recoverable:
                console.print(f"[red]Validation Error:[/] {str(e)}")
                raise typer.Exit(1)
            # allow function to continue for recoverable errors
            return None
        except JSONParsingError as e:
            console.print(f"[red]JSON Parsing Error:[/] {str(e)}")
            raise typer.Exit(1)
        except AIError as e:
            console.print(f"[red]AI Error:[/] {str(e)}")
            raise typer.Exit(1)
        except EditError as e:
            console.print(f"[red]Edit Error:[/] {str(e)}")
            raise typer.Exit(1)
        except ConfigurationError as e:
            console.print(f"[red]Configuration Error:[/] {str(e)}")
            raise typer.Exit(1)
        except LaTeXError as e:
            console.print(f"[red]LaTeX Error:[/] {str(e)}")
            raise typer.Exit(1)
        except LoomError as e:
            console.print(f"[red]Error:[/] {str(e)}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected Error:[/] {str(e)}")
            raise typer.Exit(1)
    return wrapper