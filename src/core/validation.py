# src/core/validation.py
# Strategy pattern implementation for validation error handling

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable, Any, Optional
from pathlib import Path
import typer
import json
from .constants import ValidationPolicy
from .exceptions import ValidationError


# validation outcome for strategy results
@dataclass
class ValidationOutcome:
    success: bool
    value: Any = None
    should_continue: bool = False

# base class for validation strategies
class ValidationStrategy(ABC):
    @abstractmethod
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        raise NotImplementedError

# interactive strategy that prompts user for choice
class AskStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:

        if not sys.stdin.isatty():
            error_warnings = ["Validation failed (ask not possible - non-interactive):"] + warnings
            raise ValidationError(error_warnings, recoverable=False)
        
        # print warnings
        ui.print()
        ui.print("⚠️  Validation errors found:")
        for warning in warnings:
            ui.print(f"   {warning}")
        
        while True:
            ui.print()
            with ui.input_mode():
                choice = ui.ask("Choose: [bold white](f)[/]soft-fail, [bold white](h)[/]ard-fail, [bold white](m)[/]anual, [bold white](r)[/]etry: ").lower().strip()
            
            if choice in ['s', 'soft', 'fail:soft']:
                return FailSoftStrategy().handle(warnings, ui, settings)
            elif choice in ['h', 'hard', 'fail:hard']:
                return FailHardStrategy().handle(warnings, ui, settings)
            elif choice in ['m', 'manual']:
                return ManualStrategy().handle(warnings, ui, settings)
            elif choice in ['r', 'retry']:
                return RetryStrategy().handle(warnings, ui, settings)
            else:
                ui.print("Invalid choice. Please enter f, h, m, or r.")

# retry strategy that signals to re-run validation
class RetryStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        return ValidationOutcome(success=False, should_continue=True)

# manual strategy that returns control for user intervention
class ManualStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        if not sys.stdin.isatty():
            error_warnings = ["Manual mode not available (not a TTY):"] + warnings
            raise ValidationError(error_warnings, recoverable=False)
        
        return ValidationOutcome(success=False, should_continue=False)

# fail soft strategy that quits cleanly leaving files intact
class FailSoftStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        if ui:
            ui.print("🔶 Validation failed (soft fail) - leaving files intact for inspection:")
            for warning in warnings:
                ui.print(f"   {warning}")
            if settings:
                ui.print(f"   Edits: {settings.edits_path}")
                if settings.diff_path.exists():
                    ui.print(f"   Diff: {settings.diff_path}")
                if settings.plan_path.exists():
                    ui.print(f"   Plan: {settings.plan_path}")
        
        raise typer.Exit(0)

# fail hard strategy that deletes progress files and exits
class FailHardStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui, settings=None) -> ValidationOutcome:
        if ui:
            ui.print("🔴 Validation failed (hard fail) - cleaning up progress files:")
            for warning in warnings:
                ui.print(f"   {warning}")
        
        # delete progress files
        deleted_files = []
        if settings:
            files_to_delete = [
                settings.edits_path,
                settings.diff_path,
                settings.plan_path,
                settings.warnings_path
            ]
            
            for file_path in files_to_delete:
                if file_path.exists():
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                    except Exception as e:
                        if ui:
                            ui.print(f"   ⚠️  Could not delete {file_path}: {e}")
            
            if ui and deleted_files:
                ui.print("   Deleted files:")
                for deleted in deleted_files:
                    ui.print(f"     - {deleted}")
        
        raise typer.Exit(1)

# validate using strategy pattern
def validate(validate_fn: Callable[[], List[str]], 
             policy: ValidationPolicy, 
             ui, 
             settings=None) -> ValidationOutcome:
    # map policies to strategies
    strategies = {
        ValidationPolicy.ASK: AskStrategy(),
        ValidationPolicy.RETRY: RetryStrategy(),
        ValidationPolicy.MANUAL: ManualStrategy(),
        ValidationPolicy.FAIL_SOFT: FailSoftStrategy(),
        ValidationPolicy.FAIL_HARD: FailHardStrategy(),
    }
    
    strategy = strategies.get(policy, AskStrategy())
    
    # run validation
    warnings = validate_fn()
    
    # if no warnings, validation passed
    if not warnings:
        return ValidationOutcome(success=True)
    
    # handle warnings w/ strategy
    return strategy.handle(warnings, ui, settings)


# handle validation errors w/ strategy pattern - centralized validation flow
def handle_validation_error(settings,
                           validate_fn: Callable[[], List[str]], 
                           policy: ValidationPolicy,
                           edit_fn: Optional[Callable[[List[str]], Any]] = None,
                           reload_fn: Optional[Callable[[Any], None]] = None,
                           ui=None) -> Any:
    result = None
    while True:
        outcome = validate(validate_fn, policy, ui, settings)

        if outcome.success:
            return result if result is not None else True

        # treat either an explicit RETRY policy or a user 'r' choice as "retry"
        want_retry = outcome.should_continue or policy == ValidationPolicy.RETRY

        if want_retry:
            if edit_fn is None:
                if ui:
                    ui.print("❌ Retry requested but no AI correction is available; switching to manual...")
                # fall through to manual path below
            else:
                # generate corrected edits via LLM
                warnings = validate_fn()
                result = edit_fn(warnings)
                settings.loom_dir.mkdir(exist_ok=True)
                settings.edits_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                if ui:
                    ui.print("✅ Generated corrected edits, re-validating...")
                # loop & re-validate
                continue

        # manual path (either chosen by user in ASK mode or as fallback)
        warnings = validate_fn()
        if ui:
            ui.print(f"⚠️  Validation errors found. Please edit {settings.edits_path} manually:")
            for w in warnings:
                ui.print(f"   {w}")

            while True:
                with ui.input_mode():
                    ui.ask("Press Enter after editing edits.json to re-validate...")

                try:
                    text = settings.edits_path.read_text(encoding="utf-8")
                    data = json.loads(text)
                    if reload_fn is not None:
                        reload_fn(data)
                    if ui: ui.print("✅ File edited, re-validating...")
                    break
                except json.JSONDecodeError as e:
                    # create a trimmed snippet for the error
                    try:
                        text = settings.edits_path.read_text(encoding="utf-8")
                        lines = text.split('\n')
                        line_num = e.lineno - 1
                        snippet_start = max(0, line_num - 1)
                        snippet_end = min(len(lines), line_num + 2)
                        snippet = '\n'.join(f"{i+snippet_start+1}: {lines[i+snippet_start]}" for i in range(snippet_end - snippet_start))
                        if ui: ui.print(f"❌ JSON error in edits.json at line {e.lineno}:\n{snippet}\n{e.msg}")
                    except:
                        if ui: ui.print(f"❌ JSON error in edits.json: {e}")
                    continue
                except FileNotFoundError as e:
                    if ui: ui.print(f"❌ File not found: {e}")
                    continue