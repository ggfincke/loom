# src/cli/validation_handlers.py
# CLI-layer validation I/O handlers & strategy classes
# Handles file I/O & user interaction for validation flows, keeping core pure

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable, Any, Optional

from ..core.constants import ValidationPolicy
from ..core.validation import ValidationOutcome
from ..core.exceptions import ValidationError, JSONParsingError
from ..config.settings import LoomSettings, settings_manager
from ..loom_io.generics import ensure_parent, read_json_safe
from ..ai.models import OPENAI_MODELS, get_model_description
from ..ai.provider_validator import validate_model


# Validation Strategy Classes (moved from core/validation.py)


# * Base class for validation strategies
class ValidationStrategy(ABC):
    # Ensure running in interactive terminal
    def ensure_interactive(self, mode_name: str, warnings: List[str]) -> None:
        if not sys.stdin.isatty():
            error_warnings = [
                f"{mode_name} not available - non-interactive terminal"
            ] + warnings
            raise ValidationError(error_warnings, recoverable=False)

    @abstractmethod
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        raise NotImplementedError


# * Interactive strategy that prompts user for choice
class AskStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        self.ensure_interactive("Ask mode", warnings)

        # Display warnings to user
        ui.print()
        ui.print("Validation errors found:")
        for warning in warnings:
            ui.print(f"   {warning}")

        while True:
            ui.print()
            with ui.input_mode():
                choice = (
                    ui.ask(
                        "Choose: [bold white](s)[/]oft-fail, [bold white](h)[/]ard-fail, [bold white](m)[/]anual, [bold white](r)[/]etry, [bold white](c)[/]hange-model: "
                    )
                    .lower()
                    .strip()
                )

            if choice in ["s", "soft", "fail:soft"]:
                return FailSoftStrategy().handle(warnings, ui, settings)
            elif choice in ["h", "hard", "fail:hard"]:
                return FailHardStrategy().handle(warnings, ui, settings)
            elif choice in ["m", "manual"]:
                return ManualStrategy().handle(warnings, ui, settings)
            elif choice in ["r", "retry"]:
                return RetryStrategy().handle(warnings, ui, settings)
            elif choice in ["c", "change", "change-model", "different", "model"]:
                return ModelRetryStrategy().handle(warnings, ui, settings)
            else:
                ui.print("Invalid choice. Please enter s, h, m, r, or c.")


# * Retry strategy that signals to re-run validation
class RetryStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        return ValidationOutcome(success=False, should_continue=True, value=warnings)


# * Manual strategy that returns control for user intervention
class ManualStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        self.ensure_interactive("Manual mode", warnings)
        return ValidationOutcome(success=False, should_continue=False)


# * Fail soft strategy that quits cleanly leaving files intact
class FailSoftStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        if ui:
            ui.print(
                "🔶 Validation failed (soft fail) - leaving files intact for inspection:"
            )
            for warning in warnings:
                ui.print(f"   {warning}")
            if settings:
                ui.print(f"   Edits: {settings.edits_path}")
                if settings.diff_path.exists():
                    ui.print(f"   Diff: {settings.diff_path}")
                if settings.plan_path.exists():
                    ui.print(f"   Plan: {settings.plan_path}")

        raise SystemExit(0)


# * Model retry strategy that prompts user to select different model
class ModelRetryStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        self.ensure_interactive("Model change", warnings)

        # Build model options from source of truth (OpenAI only for now)
        model_options = [
            (str(i + 1), model, get_model_description(model))
            for i, model in enumerate(OPENAI_MODELS)
        ]
        max_option = len(model_options)

        ui.print()
        ui.print("📋 Select a different model to retry with:")
        for num, model, desc in model_options:
            ui.print(f"   {num}) {model} - {desc}")

        while True:
            ui.print()
            with ui.input_mode():
                choice = ui.ask(
                    f"Enter model number (1-{max_option}) or model name: "
                ).strip()

            # Convert user choice to model name
            selected_model = None

            # Check numeric selection
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= max_option:
                    selected_model = model_options[idx - 1][1]
                else:
                    ui.print(
                        f"Invalid choice. Please enter a number (1-{max_option}) or valid model name."
                    )
                    continue
            elif choice in OPENAI_MODELS:
                # Direct model name for OpenAI models
                selected_model = choice
            elif choice.startswith("gpt-"):
                # Validate model against supported list
                valid, _ = validate_model(choice)
                if valid:
                    selected_model = choice
                else:
                    ui.print(
                        f"Model '{choice}' is not supported. Supported models: {', '.join(OPENAI_MODELS)}"
                    )
                    continue
            else:
                ui.print(
                    f"Invalid choice. Please enter a number (1-{max_option}) or valid model name."
                )
                continue

            # Update settings w/ new model
            if settings:
                current_settings = settings_manager.load()
                current_settings.model = selected_model
                settings_manager.save(current_settings)
                ui.print(f"✅ Model changed to {selected_model}, retrying...")

            return ValidationOutcome(
                success=False, should_continue=True, value=selected_model
            )


# * Fail hard strategy that deletes progress files & exits
class FailHardStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        if ui:
            ui.print("🔴 Validation failed (hard fail) - cleaning up progress files:")
            for warning in warnings:
                ui.print(f"   {warning}")

        # Clean up progress files
        deleted_files = []
        if settings:
            files_to_delete = [
                settings.edits_path,
                settings.diff_path,
                settings.plan_path,
                settings.warnings_path,
            ]

            for file_path in files_to_delete:
                if file_path.exists():
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                    except Exception as e:
                        if ui:
                            ui.print(f"   Could not delete {file_path}: {e}")

            if ui and deleted_files:
                ui.print("   Deleted files:")
                for deleted in deleted_files:
                    ui.print(f"     - {deleted}")

        raise SystemExit(1)


# Validation Execution (moved from core/validation.py)


# * Validate using strategy pattern
def validate(
    validate_fn: Callable[[], List[str]], policy: ValidationPolicy, ui, settings=None
) -> ValidationOutcome:
    # Convert policies to strategy instances
    strategies = {
        ValidationPolicy.ASK: AskStrategy(),
        ValidationPolicy.RETRY: RetryStrategy(),
        ValidationPolicy.MANUAL: ManualStrategy(),
        ValidationPolicy.FAIL_SOFT: FailSoftStrategy(),
        ValidationPolicy.FAIL_HARD: FailHardStrategy(),
    }

    strategy = strategies.get(policy, AskStrategy())

    # Execute validation function
    warnings = validate_fn()

    # Return success if no warnings found
    if not warnings:
        return ValidationOutcome(success=True)

    # Process warnings using selected strategy
    return strategy.handle(warnings, ui, settings)


# High-Level Validation Handler


# * Handle validation errors w/ strategy pattern - centralized validation flow
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

        # Handle retry policy or user retry selection
        want_retry = outcome.should_continue or policy == ValidationPolicy.RETRY

        if want_retry:
            if edit_fn is None:
                if ui:
                    ui.print(
                        "Retry requested but no AI correction is available; switching to manual..."
                    )
                # Fall through to manual path below
            else:
                # Use AI to generate corrected edits
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
                # Continue loop for re-validation
                continue

        # Handle manual editing path
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
                    # Read_json_safe provides formatted error w/ snippet
                    if ui:
                        ui.print(str(e))
                    continue
                except FileNotFoundError as e:
                    if ui:
                        ui.print(f"File not found: {e}")
                    continue
