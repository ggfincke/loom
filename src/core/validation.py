# src/core/validation.py
# Strategy pattern implementation for validation error handling

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable, Any
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
    def handle(self, warnings: List[str], ui) -> ValidationOutcome:
        raise NotImplementedError

# interactive strategy that prompts user for choice
class AskStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui) -> ValidationOutcome:
        if not sys.stdin.isatty():
            error_warnings = ["Validation failed (ask not possible - non-interactive):"] + warnings
            raise ValidationError(error_warnings, recoverable=False)
        
        # Print warnings
        ui.print()
        ui.print("⚠️  Validation errors found:")
        for warning in warnings:
            ui.print(f"   {warning}")
        
        while True:
            ui.print()
            with ui.input_mode():
                choice = ui.ask("Choose: [bold white](f)[/]ail-soft, [bold white](h)[/]ard-fail, [bold white](m)[/]anual, [bold white](r)[/]etry: ").lower().strip()
            
            if choice in ['f', 'fail', 'fail:soft']:
                return FailSoftStrategy().handle(warnings, ui)
            elif choice in ['h', 'hard', 'fail:hard']:
                return FailHardStrategy().handle(warnings, ui)
            elif choice in ['m', 'manual']:
                return ManualStrategy().handle(warnings, ui)
            elif choice in ['r', 'retry']:
                return RetryStrategy().handle(warnings, ui)
            else:
                ui.print("Invalid choice. Please enter f, h, m, or r.")

# retry strategy that signals to re-run validation
class RetryStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui) -> ValidationOutcome:
        return ValidationOutcome(success=False, should_continue=True)

# manual strategy that returns control for user intervention
class ManualStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui) -> ValidationOutcome:
        if not sys.stdin.isatty():
            error_warnings = ["Manual mode not available (not a TTY):"] + warnings
            raise ValidationError(error_warnings, recoverable=False)
        
        return ValidationOutcome(success=False, should_continue=False)

# fail soft strategy that raises recoverable error
class FailSoftStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui) -> ValidationOutcome:
        raise ValidationError(warnings, recoverable=True)

# fail hard strategy that raises non-recoverable error
class FailHardStrategy(ValidationStrategy):
    def handle(self, warnings: List[str], ui) -> ValidationOutcome:
        error_warnings = ["Validation failed (hard):"] + warnings
        raise ValidationError(error_warnings, recoverable=False)

# validate using strategy pattern
def validate(validate_fn: Callable[[], List[str]], 
             policy: ValidationPolicy, 
             ui) -> ValidationOutcome:
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
    return strategy.handle(warnings, ui)