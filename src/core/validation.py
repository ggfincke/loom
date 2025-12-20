# src/core/validation.py
# Strategy pattern implementation for validation error handling

import sys
import json
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable, Any, Optional, Dict
from pathlib import Path
from .constants import ValidationPolicy, RiskLevel
from .exceptions import ValidationError, JSONParsingError
from ..ai.models import SUPPORTED_MODELS, validate_model
from ..config.settings import settings_manager, LoomSettings
from ..loom_io.generics import ensure_parent
from .edit_helpers import (
    check_line_exists,
    check_range_exists,
    check_range_usage,
    count_text_lines,
    validate_line_number,
    validate_operation_interactions,
    validate_range_bounds,
    validate_required_fields,
    validate_text_field,
    OP_REPLACE_LINE,
    OP_REPLACE_RANGE,
    OP_INSERT_AFTER,
    OP_DELETE_RANGE,
)


# * Validation outcome for strategy results
@dataclass
class ValidationOutcome:
    success: bool
    value: Any = None
    should_continue: bool = False


# * Base class for validation strategies
class ValidationStrategy(ABC):
    @abstractmethod
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        raise NotImplementedError


# * Interactive strategy that prompts user for choice
class AskStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:

        if not sys.stdin.isatty():
            error_warnings = ["ask not possible - non-interactive"] + warnings
            raise ValidationError(error_warnings, recoverable=False)

        # display warnings to user
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
        if not sys.stdin.isatty():
            error_warnings = ["Manual mode not available (not a TTY)"] + warnings
            raise ValidationError(error_warnings, recoverable=False)

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
        if not sys.stdin.isatty():
            error_warnings = ["Model change not available (not a TTY):"] + warnings
            raise ValidationError(error_warnings, recoverable=False)

        # available model options for selection
        model_options = [
            ("1", "gpt-5", "GPT-5 (latest, most capable)"),
            ("2", "gpt-5-mini", "GPT-5 Mini (latest generation, cost-efficient)"),
            ("3", "gpt-5-nano", "GPT-5 Nano (fastest, ultra-low latency)"),
            ("4", "gpt-4o", "GPT-4o (multimodal, high capability)"),
            ("5", "gpt-4o-mini", "GPT-4o Mini (fast, cost-effective)"),
        ]

        ui.print()
        ui.print("📋 Select a different model to retry with:")
        for num, model, desc in model_options:
            ui.print(f"   {num}) {model} - {desc}")

        while True:
            ui.print()
            with ui.input_mode():
                choice = ui.ask("Enter model number (1-5) or model name: ").strip()

            # convert user choice to model name
            selected_model = None
            if choice in ["1"]:
                selected_model = "gpt-5"
            elif choice in ["2"]:
                selected_model = "gpt-5-mini"
            elif choice in ["3"]:
                selected_model = "gpt-5-nano"
            elif choice in ["4"]:
                selected_model = "gpt-4o"
            elif choice in ["5"]:
                selected_model = "gpt-4o-mini"
            elif choice.startswith("gpt-"):
                # validate model against supported list
                valid, _ = validate_model(choice)
                if valid:
                    selected_model = choice
                else:
                    ui.print(
                        f"Model '{choice}' is not supported. Supported models: {', '.join(SUPPORTED_MODELS)}"
                    )
                    continue
            else:
                ui.print(
                    "Invalid choice. Please enter a number (1-5) or valid model name."
                )
                continue

            # update settings w/ new model
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

        # clean up progress files
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


# * Validate using strategy pattern
def validate(
    validate_fn: Callable[[], List[str]], policy: ValidationPolicy, ui, settings=None
) -> ValidationOutcome:
    # convert policies to strategy instances
    strategies = {
        ValidationPolicy.ASK: AskStrategy(),
        ValidationPolicy.RETRY: RetryStrategy(),
        ValidationPolicy.MANUAL: ManualStrategy(),
        ValidationPolicy.FAIL_SOFT: FailSoftStrategy(),
        ValidationPolicy.FAIL_HARD: FailHardStrategy(),
    }

    strategy = strategies.get(policy, AskStrategy())

    # execute validation function
    warnings = validate_fn()

    # return success if no warnings found
    if not warnings:
        return ValidationOutcome(success=True)

    # process warnings using selected strategy
    return strategy.handle(warnings, ui, settings)


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
                    ui.print("✅ Generated corrected edits, re-validating...")
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
                    # ! use centralized read_json_safe for consistent error handling
                    from ..loom_io.generics import read_json_safe

                    data = read_json_safe(settings.edits_path)
                    if reload_fn is not None:
                        reload_fn(data)
                    if ui:
                        ui.print("✅ File edited, re-validating...")
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


# * Edit JSON validation logic (moved from pipeline.py)


def validate_edits(
    edits: dict, resume_lines: dict[int, str], risk: RiskLevel
) -> List[str]:
    warnings: List[str] = []

    if "ops" not in edits:
        warnings.append("Missing 'ops' field in edits")
        return warnings

    ops = edits["ops"]
    if not isinstance(ops, list):
        warnings.append("'ops' field must be a list")
        return warnings

    if len(ops) == 0:
        warnings.append("'ops' list is empty")
        return warnings

    line_usage: dict[int, str] = {}

    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            warnings.append(f"Op {i}: must be an object")
            continue

        op_type = op.get("op")
        if not op_type:
            warnings.append(f"Op {i}: missing 'op' field")
            continue

        if op_type == OP_REPLACE_LINE:
            # Required fields check
            is_valid, error = validate_required_fields(
                op, ["line", "text"], "replace_line", i
            )
            if not is_valid:
                warnings.append(error)
                continue

            # Line number validation
            line = op["line"]
            is_valid, error = validate_line_number(line, i)
            if not is_valid:
                warnings.append(error)
                continue

            # Text validation (no newlines for replace_line)
            is_valid, error = validate_text_field(op["text"], allow_newlines=False, op_index=i)
            if not is_valid:
                warnings.append(error)
                continue

            # Bounds check
            if not check_line_exists(line, resume_lines):
                warnings.append(f"Op {i}: line {line} not in resume bounds")
                continue

            # Duplicate check
            if line in line_usage:
                warnings.append(f"Op {i}: duplicate operation on line {line}")
            line_usage[line] = op_type

        elif op_type == OP_REPLACE_RANGE:
            # Required fields check
            is_valid, error = validate_required_fields(
                op, ["start", "end", "text"], "replace_range", i
            )
            if not is_valid:
                warnings.append(error)
                continue

            # Range bounds validation
            start, end = op["start"], op["end"]
            is_valid, error = validate_range_bounds(start, end, i)
            if not is_valid:
                warnings.append(error)
                continue

            # Text validation
            is_valid, error = validate_text_field(op["text"], allow_newlines=True, op_index=i)
            if not is_valid:
                warnings.append(error)
                continue

            # Range exists check
            exists, missing_line = check_range_exists(start, end, resume_lines)
            if not exists:
                warnings.append(f"Op {i}: line {missing_line} not in resume bounds")
                continue

            # Line count mismatch check
            text_line_count = count_text_lines(op["text"])
            range_line_count = end - start + 1
            if text_line_count != range_line_count:
                msg = f"Op {i}: replace_range line count mismatch ({range_line_count} -> {text_line_count})"
                if risk in [RiskLevel.MED, RiskLevel.HIGH, RiskLevel.STRICT]:
                    warnings.append(msg + " (will cause line collisions)")
                else:
                    warnings.append(msg)

            # Duplicate check (uses shared helper)
            dup_warnings = check_range_usage(start, end, line_usage, op_type, i)
            warnings.extend(dup_warnings)

        elif op_type == OP_INSERT_AFTER:
            # Required fields check
            is_valid, error = validate_required_fields(
                op, ["line", "text"], "insert_after", i
            )
            if not is_valid:
                warnings.append(error)
                continue

            # Line number validation
            line = op["line"]
            is_valid, error = validate_line_number(line, i)
            if not is_valid:
                warnings.append(error)
                continue

            # Text validation
            is_valid, error = validate_text_field(op["text"], allow_newlines=True, op_index=i)
            if not is_valid:
                warnings.append(error)
                continue

            # Bounds check
            if not check_line_exists(line, resume_lines):
                warnings.append(f"Op {i}: line {line} not in resume bounds")
                continue

        elif op_type == OP_DELETE_RANGE:
            # Required fields check
            is_valid, error = validate_required_fields(
                op, ["start", "end"], "delete_range", i
            )
            if not is_valid:
                warnings.append(error)
                continue

            # Range bounds validation
            start, end = op["start"], op["end"]
            is_valid, error = validate_range_bounds(start, end, i)
            if not is_valid:
                warnings.append(error)
                continue

            # Range exists check
            exists, missing_line = check_range_exists(start, end, resume_lines)
            if not exists:
                warnings.append(f"Op {i}: line {missing_line} not in resume bounds")
                continue

            # Duplicate check (uses shared helper)
            dup_warnings = check_range_usage(start, end, line_usage, op_type, i)
            warnings.extend(dup_warnings)

        else:
            warnings.append(f"Op {i}: unknown operation type '{op_type}'")

    # Cross-operation conflict detection (uses shared helper)
    warnings.extend(validate_operation_interactions(ops))

    return warnings


