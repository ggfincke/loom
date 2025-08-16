# src/core/exceptions.py
# Custom exception hierarchy and centralized error handling for Loom

import functools
from typing import List
import typer
from ..loom_io.console import console

# base exception for Loom application
class LoomError(Exception):
    pass

# validation-specific error for handling warnings and recoverable errors (w/ warning context)
class ValidationError(LoomError):    
    def __init__(self, warnings: List[str], recoverable: bool = True):
        self.warnings = warnings
        self.recoverable = recoverable
        message = f"Validation failed with {len(warnings)} warnings"
        super().__init__(message)

# AI exception
class AIError(LoomError):
    pass

# Edit application errors
class EditError(LoomError):
    pass

# Configuration errors
class ConfigurationError(LoomError):
    pass

# JSON parsing errors
class JSONParsingError(LoomError):
    pass


# decorator for handling Loom errors in CLI commands
def handle_loom_error(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            if not e.recoverable:
                console.print(f"[red]Validation Error:[/] {str(e)}")
                raise typer.Exit(1)
            # for recoverable validation errors, let the function continue
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
        except LoomError as e:
            console.print(f"[red]Error:[/] {str(e)}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected Error:[/] {str(e)}")
            raise typer.Exit(1)
    return wrapper