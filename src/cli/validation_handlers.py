# src/cli/validation_handlers.py
# CLI-layer validation I/O handlers - extracted from core/validation.py
# Handles file I/O & user interaction for validation flows, keeping core pure

import json
from typing import List, Callable, Any, Optional

from ..core.constants import ValidationPolicy
from ..core.validation import validate, ValidationOutcome
from ..core.exceptions import JSONParsingError
from ..config.settings import LoomSettings
from ..loom_io.generics import ensure_parent, read_json_safe


# * Handle validation errors w/ strategy pattern - centralized validation flow
# * Extracted from core/validation.py to keep core layer I/O-free
def handle_validation_error(
    settings: LoomSettings | None,
    validate_fn: Callable[[], List[str]],
    policy: ValidationPolicy,
    edit_fn: Optional[Callable[[List[str]], Any]] = None,
    reload_fn: Optional[Callable[[Any], None]] = None,
    ui=None,
) -> Any:
    result = None
    while True:
        outcome = validate(validate_fn, policy, ui, settings)

        if outcome.success:
            return result if result is not None else True

        # handle retry policy or user retry selection
        want_retry = outcome.should_continue or policy == ValidationPolicy.RETRY

        if want_retry:
            if edit_fn is None:
                if ui:
                    ui.print(
                        "Retry requested but no AI correction is available; switching to manual..."
                    )
                # fall through to manual path below
            else:
                # use AI to generate corrected edits
                prior_warnings: List[str] = (
                    outcome.value if isinstance(outcome.value, list) else []
                )
                result = edit_fn(prior_warnings)
                if settings is not None:
                    settings.loom_dir.mkdir(parents=True, exist_ok=True)
                    ensure_parent(settings.edits_path)
                    settings.edits_path.write_text(
                        json.dumps(result, indent=2), encoding="utf-8"
                    )
                if ui:
                    ui.print("Generated corrected edits, re-validating...")
                # continue loop for re-validation
                continue

        # handle manual editing path
        warnings = validate_fn()
        if ui and settings is not None:
            ui.print(
                f"Validation errors found. Please edit {settings.edits_path} manually:"
            )
            for w in warnings:
                ui.print(f"   {w}")

            while True:
                with ui.input_mode():
                    ui.ask("Press Enter after editing edits.json to re-validate...")

                try:
                    if settings is None:
                        break
                    data = read_json_safe(settings.edits_path)
                    if reload_fn is not None:
                        reload_fn(data)
                    if ui:
                        ui.print("File edited, re-validating...")
                    break
                except JSONParsingError as e:
                    # read_json_safe provides formatted error w/ snippet
                    if ui:
                        ui.print(str(e))
                    continue
                except FileNotFoundError as e:
                    if ui:
                        ui.print(f"File not found: {e}")
                    continue
