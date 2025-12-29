# src/cli/model_helpers.py
# CLI-layer model validation helpers (contains I/O operations)

import typer

from ..ai.models import resolve_model_alias
from ..ai.provider_validator import validate_model, get_model_error_message


# * Validate model & exit if invalid (CLI I/O wrapper)
def ensure_valid_model_cli(model: str | None) -> str | None:
    if model is None:
        return None

    # resolve alias first
    resolved_model = resolve_model_alias(model)

    valid, _ = validate_model(resolved_model)
    if not valid:
        typer.echo(get_model_error_message(model), err=True)
        raise typer.Exit(1)

    return resolved_model
