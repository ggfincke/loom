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


# decorator for handling Loom errors in CLI commands
def handle_loom_error(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            console.print("❌ Validation failed:", style="red")
            for warning in e.warnings:
                console.print(f"   {warning}", style="yellow")
            if not e.recoverable:
                raise typer.Exit(1)
            # for recoverable validation errors, let the function continue
            return None
        except LoomError as e:
            console.print(f"❌ {e}", style="red")
            raise typer.Exit(1)
    return wrapper