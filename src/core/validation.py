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
from .exceptions import ValidationError
from ..ai.models import SUPPORTED_MODELS, validate_model
from ..config.settings import settings_manager, LoomSettings
from ..loom_io.generics import ensure_parent


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
        ui.print("⚠️  Validation errors found:")
        for warning in warnings:
            ui.print(f"   {warning}")
        
        while True:
            ui.print()
            with ui.input_mode():
                choice = ui.ask("Choose: [bold white](s)[/]oft-fail, [bold white](h)[/]ard-fail, [bold white](m)[/]anual, [bold white](r)[/]etry, [bold white](c)[/]hange-model: ").lower().strip()
            
            if choice in ['s', 'soft', 'fail:soft']:
                return FailSoftStrategy().handle(warnings, ui, settings)
            elif choice in ['h', 'hard', 'fail:hard']:
                return FailHardStrategy().handle(warnings, ui, settings)
            elif choice in ['m', 'manual']:
                return ManualStrategy().handle(warnings, ui, settings)
            elif choice in ['r', 'retry']:
                return RetryStrategy().handle(warnings, ui, settings)
            elif choice in ['c', 'change', 'change-model', 'different', 'model']:
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
            ui.print("🔶 Validation failed (soft fail) - leaving files intact for inspection:")
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
            ("5", "gpt-4o-mini", "GPT-4o Mini (fast, cost-effective)")
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
            if choice in ['1']:
                selected_model = "gpt-5"
            elif choice in ['2']:
                selected_model = "gpt-5-mini"
            elif choice in ['3']:
                selected_model = "gpt-5-nano"
            elif choice in ['4']:
                selected_model = "gpt-4o"
            elif choice in ['5']:
                selected_model = "gpt-4o-mini"
            elif choice.startswith('gpt-'):
                # validate model against supported list
                valid, _ = validate_model(choice)
                if valid:
                    selected_model = choice
                else:
                    ui.print(f"Model '{choice}' is not supported. Supported models: {', '.join(SUPPORTED_MODELS)}")
                    continue
            else:
                ui.print("Invalid choice. Please enter a number (1-5) or valid model name.")
                continue
            
            # update settings w/ new model
            if settings:
                current_settings = settings_manager.load()
                current_settings.model = selected_model
                settings_manager.save(current_settings)
                ui.print(f"✅ Model changed to {selected_model}, retrying...")
            
            return ValidationOutcome(success=False, should_continue=True, value=selected_model)

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
        
        raise SystemExit(1)

# * Validate using strategy pattern
def validate(validate_fn: Callable[[], List[str]], 
             policy: ValidationPolicy, 
             ui, 
             settings=None) -> ValidationOutcome:
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
def handle_validation_error(settings: LoomSettings | None,
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

        # handle retry policy or user retry selection
        want_retry = outcome.should_continue or policy == ValidationPolicy.RETRY

        if want_retry:
            if edit_fn is None:
                if ui:
                    ui.print("❌ Retry requested but no AI correction is available; switching to manual...")
                # fall through to manual path below
            else:
                # use AI to generate corrected edits
                prior_warnings: List[str] = outcome.value if isinstance(outcome.value, list) else []
                result = edit_fn(prior_warnings)
                if settings is not None:
                    settings.loom_dir.mkdir(parents=True, exist_ok=True)
                    ensure_parent(settings.edits_path)
                    settings.edits_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                if ui:
                    ui.print("✅ Generated corrected edits, re-validating...")
                # continue loop for re-validation
                continue

        # handle manual editing path
        warnings = validate_fn()
        if ui and settings is not None:
            ui.print(f"⚠️  Validation errors found. Please edit {settings.edits_path} manually:")
            for w in warnings:
                ui.print(f"   {w}")

            while True:
                with ui.input_mode():
                    ui.ask("Press Enter after editing edits.json to re-validate...")

                try:
                    if settings is None:
                        break
                    text = settings.edits_path.read_text(encoding="utf-8")
                    data = json.loads(text)
                    if reload_fn is not None:
                        reload_fn(data)
                    if ui: ui.print("✅ File edited, re-validating...")
                    break
                except json.JSONDecodeError as e:
                    # generate error context snippet
                    try:
                        if settings is None:
                            continue
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

# * Edit JSON validation logic (moved from pipeline.py)

def validate_edits(edits: dict, resume_lines: dict[int, str], risk: RiskLevel) -> List[str]:
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

        if op_type == "replace_line":
            if "line" not in op:
                warnings.append(f"Op {i}: replace_line missing 'line' field")
                continue
            if "text" not in op:
                warnings.append(f"Op {i}: replace_line missing 'text' field")
                continue

            line = op["line"]
            if not isinstance(line, int) or line < 1:
                warnings.append(f"Op {i}: 'line' must be integer >= 1")
                continue

            if not isinstance(op["text"], str):
                warnings.append(f"Op {i}: 'text' must be string")
                continue

            if "\n" in op["text"]:
                warnings.append(f"Op {i}: replace_line text contains newline; use replace_range")
                continue

            if line not in resume_lines:
                warnings.append(f"Op {i}: line {line} not in resume bounds")
                continue

            if line in line_usage:
                warnings.append(f"Op {i}: duplicate operation on line {line}")
            line_usage[line] = op_type

        elif op_type == "replace_range":
            if "start" not in op or "end" not in op or "text" not in op:
                warnings.append(f"Op {i}: replace_range missing required fields (start, end, text)")
                continue

            start, end = op["start"], op["end"]
            if not isinstance(start, int) or not isinstance(end, int):
                warnings.append(f"Op {i}: start and end must be integers")
                continue

            if start < 1 or end < 1 or start > end:
                warnings.append(f"Op {i}: invalid range {start}-{end}")
                continue

            if not isinstance(op["text"], str):
                warnings.append(f"Op {i}: 'text' must be string")
                continue

            for line in range(start, end + 1):
                if line not in resume_lines:
                    warnings.append(f"Op {i}: line {line} not in resume bounds")
                    break

            if op["text"]:
                text_line_count = len(op["text"].split("\n"))
            else:
                text_line_count = 1
            range_line_count = end - start + 1
            if text_line_count != range_line_count:
                msg = f"Op {i}: replace_range line count mismatch ({range_line_count} -> {text_line_count})"
                if risk in [RiskLevel.MED, RiskLevel.HIGH, RiskLevel.STRICT]:
                    warnings.append(msg + " (will cause line collisions)")
                else:
                    warnings.append(msg)

            for line in range(start, end + 1):
                if line in line_usage:
                    warnings.append(f"Op {i}: duplicate operation on line {line}")
                    break
            for line in range(start, end + 1):
                line_usage[line] = op_type

        elif op_type == "insert_after":
            if "line" not in op or "text" not in op:
                warnings.append(f"Op {i}: insert_after missing required fields (line, text)")
                continue

            line = op["line"]
            if not isinstance(line, int) or line < 1:
                warnings.append(f"Op {i}: 'line' must be integer >= 1")
                continue

            if not isinstance(op["text"], str):
                warnings.append(f"Op {i}: 'text' must be string")
                continue

            if line not in resume_lines:
                warnings.append(f"Op {i}: line {line} not in resume bounds")
                continue

        elif op_type == "delete_range":
            if "start" not in op or "end" not in op:
                warnings.append(f"Op {i}: delete_range missing required fields (start, end)")
                continue

            start, end = op["start"], op["end"]
            if not isinstance(start, int) or not isinstance(end, int):
                warnings.append(f"Op {i}: start and end must be integers")
                continue

            if start < 1 or end < 1 or start > end:
                warnings.append(f"Op {i}: invalid range {start}-{end}")
                continue

            for line in range(start, end + 1):
                if line not in resume_lines:
                    warnings.append(f"Op {i}: line {line} not in resume bounds")
                    break

            for line in range(start, end + 1):
                if line in line_usage:
                    warnings.append(f"Op {i}: duplicate operation on line {line}")
                    break
            for line in range(start, end + 1):
                line_usage[line] = op_type

        else:
            warnings.append(f"Op {i}: unknown operation type '{op_type}'")

    delete_ranges = [(op["start"], op["end"]) for op in ops if op.get("op") == "delete_range" and "start" in op and "end" in op]
    for i, op in enumerate(ops):
        if op.get("op") == "insert_after" and "line" in op:
            ln = op["line"]
            if any(s <= ln <= e for s, e in delete_ranges):
                warnings.append(f"Op {i}: insert_after on line {ln} that is deleted by a delete_range")

    replace_ranges = [(op["start"], op["end"]) for op in ops if op.get("op") == "replace_range" and "start" in op and "end" in op]
    for i, op in enumerate(ops):
        if op.get("op") == "delete_range" and "start" in op and "end" in op:
            s, e = op["start"], op["end"]
            if any(not (e2 < s or s2 > e) for (s2, e2) in replace_ranges):
                warnings.append(f"Op {i}: delete_range overlaps a replace_range; split or reorder ops")

    seen_inserts = set()
    for i, op in enumerate(ops):
        if op.get("op") == "insert_after" and "line" in op:
            ln = op["line"]
            if ln in seen_inserts:
                warnings.append(f"Op {i}: multiple insert_after on line {ln}")
            seen_inserts.add(ln)

    return warnings


# LaTeX compilation validation & syntax checking functions

# * Validate LaTeX document by attempting compilation
def validate_latex_compilation(
    content: str, 
    compiler: str = "pdflatex",
    timeout: int = 30
) -> Dict[str, Any]:
    result = {
        'success': False,
        'errors': [],
        'warnings': [],
        'compiler_available': False
    }
    
        # verify compiler availability
    try:
        subprocess.run([compiler, '--version'], 
                      capture_output=True, 
                      timeout=5, 
                      check=True)
        result['compiler_available'] = True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        result['errors'].append(f"LaTeX compiler '{compiler}' not found or not working")
        return result
    
    # setup temporary compilation environment
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tex_file = temp_path / "document.tex"
        
        try:
            # save content to temporary tex file
            tex_file.write_text(content, encoding='utf-8')
            
            # execute latex compilation command
            cmd = [
                compiler,
                '-interaction=nonstopmode',
                '-halt-on-error',
                '-output-directory', str(temp_path),
                str(tex_file)
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=temp_path
            )
            
            # extract errors & warnings from output
            output = process.stdout + process.stderr
            result['errors'].extend(_parse_latex_errors(output))
            result['warnings'].extend(_parse_latex_warnings(output))
            
            # verify successful PDF generation
            pdf_file = temp_path / "document.pdf"
            if pdf_file.exists() and process.returncode == 0:
                result['success'] = True
            else:
                if not result['errors']:
                    result['errors'].append("Compilation failed but no specific errors detected")
                    
        except subprocess.TimeoutExpired:
            result['errors'].append(f"LaTeX compilation timed out after {timeout} seconds")
        except Exception as e:
            result['errors'].append(f"Compilation error: {str(e)}")
    
    return result

# * Parse LaTeX compilation errors from output
def _parse_latex_errors(output: str) -> List[str]:
    errors = []
    lines = output.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # detect standard error patterns
        if line.startswith('!'):
            errors.append(line)
        elif 'Error:' in line:
            errors.append(line)
        elif line.startswith('l.') and ' ' in line:
            # handle line number error indicators
            try:
                # extract context from previous line
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line.startswith('!'):
                        errors.append(f"{prev_line} at {line}")
                    else:
                        errors.append(line)
                else:
                    errors.append(line)
            except IndexError:
                errors.append(line)
    
    return errors

# * Parse LaTeX compilation warnings from output
def _parse_latex_warnings(output: str) -> List[str]:
    warnings = []
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # detect standard warning patterns
        if ('Warning:' in line or 
            'warning:' in line or
            line.startswith('LaTeX Warning:') or
            'Overfull' in line or
            'Underfull' in line):
            warnings.append(line)
    
    return warnings

# * Check which LaTeX compilers are available
def check_latex_availability() -> Dict[str, bool]:
    compilers = ['pdflatex', 'xelatex', 'lualatex']
    availability = {}
    
    for compiler in compilers:
        try:
            subprocess.run([compiler, '--version'], 
                          capture_output=True, 
                          timeout=5, 
                          check=True)
            availability[compiler] = True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            availability[compiler] = False
    
    return availability

# * Basic LaTeX syntax validation (moved from loom_io/documents.py)
def validate_basic_latex_syntax(text: str) -> bool:
    brace_count = 0
    for char in text:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count < 0:
                return False
    if brace_count != 0:
        return False
    has_documentclass = '\\documentclass' in text
    has_begin_doc = '\\begin{document}' in text
    has_end_doc = '\\end{document}' in text
    if has_documentclass and not (has_begin_doc and has_end_doc):
        return False
    return True


# * Comprehensive LaTeX validation w/ optional compilation check
def validate_latex_document(
    content: str, 
    check_compilation: bool = False,
    compiler: str = "pdflatex"
) -> Dict[str, Any]:
    result = {
        'syntax_valid': False,
        'compilation_checked': False,
        'compilation_result': None,
        'errors': [],
        'warnings': []
    }
    
    # perform basic syntax validation
    try:
        result['syntax_valid'] = validate_basic_latex_syntax(content)
        if not result['syntax_valid']:
            result['errors'].append("Basic LaTeX syntax validation failed")
    except Exception as e:
        result['errors'].append(f"Syntax validation error: {str(e)}")
    
    # perform optional compilation validation
    if check_compilation and result['syntax_valid']:
        try:
            comp_result = validate_latex_compilation(content, compiler)
            result['compilation_checked'] = True
            result['compilation_result'] = comp_result
            
            # combine compilation errors & warnings
            result['errors'].extend(comp_result['errors'])
            result['warnings'].extend(comp_result['warnings'])
            
        except Exception as e:
            result['errors'].append(f"Compilation validation error: {str(e)}")
    
    return result
