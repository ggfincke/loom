# src/ui/diff_resolution/diff_state.py
# State management & AI processing for interactive diff review UI

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from rich.live import Live
    from ...core.types import Lines
    from ...core.constants import EditOperation
    from .diff_renderer import DiffRenderer


# menu options for diff review UI
OPTIONS = [
    "Approve",
    "Reject",
    "Skip",
    "Modify",
    "Prompt",
    "Exit",
]


# UI state enum for mode transitions
class DiffReviewMode(Enum):
    MENU = "menu"
    TEXT_INPUT = "text_input"
    PROMPT_PROCESSING = "processing"


# type alias for prompt regeneration callback
PromptCallback = Callable[["EditOperation", "Lines", str, str | None, str], bool]

# minimum duration for loading screen to prevent flashing
MIN_LOADING_DURATION = 1.5


@dataclass
class AIContext:

    resume_lines: "Lines | None" = None
    job_text: str | None = None
    sections_json: str | None = None
    model: str | None = None


@dataclass
class DiffState:

    # operation tracking
    operations: list["EditOperation"] = field(default_factory=list)
    filename: str = "document.txt"
    current_index: int = 0

    # menu selection
    selected: int = 0

    # mode state
    mode: DiffReviewMode = DiffReviewMode.MENU

    # text input state
    text_input_buffer: str = ""
    text_input_cursor: int = 0
    text_input_mode: str | None = None  # "modify" or "prompt"

    # prompt processing state
    prompt_error: str | None = None

    # modification tracking
    operations_modified: bool = False

    @property
    def current_operation(self) -> "EditOperation | None":
        if 0 <= self.current_index < len(self.operations):
            return self.operations[self.current_index]
        return None

    @property
    def is_complete(self) -> bool:
        return self.current_index >= len(self.operations)


class DiffStateManager:

    def __init__(self, state: DiffState):
        self.state = state

    # ===== MODE TRANSITIONS =====

    def enter_modify_mode(self) -> None:
        if self.state.current_operation:
            self.state.mode = DiffReviewMode.TEXT_INPUT
            self.state.text_input_mode = "modify"
            self.state.text_input_buffer = self.state.current_operation.content
            self.state.text_input_cursor = len(self.state.text_input_buffer)

    def enter_prompt_mode(self) -> None:
        self.state.mode = DiffReviewMode.TEXT_INPUT
        self.state.text_input_mode = "prompt"
        self.state.text_input_buffer = ""
        self.state.text_input_cursor = 0

    def enter_prompt_processing(self) -> None:
        self.state.mode = DiffReviewMode.PROMPT_PROCESSING
        self.state.prompt_error = None

    def return_to_menu(self) -> None:
        self.state.mode = DiffReviewMode.MENU
        self._reset_text_input()

    def cancel_text_input(self) -> None:
        self.state.mode = DiffReviewMode.MENU
        self._reset_text_input()
        self.state.prompt_error = None

    # ===== TEXT INPUT OPERATIONS =====

    def insert_char(self, char: str) -> None:
        self.state.text_input_buffer = (
            self.state.text_input_buffer[: self.state.text_input_cursor]
            + char
            + self.state.text_input_buffer[self.state.text_input_cursor :]
        )
        self.state.text_input_cursor += 1

    def delete_before_cursor(self) -> None:
        if self.state.text_input_cursor > 0:
            self.state.text_input_buffer = (
                self.state.text_input_buffer[: self.state.text_input_cursor - 1]
                + self.state.text_input_buffer[self.state.text_input_cursor :]
            )
            self.state.text_input_cursor -= 1

    def move_cursor_left(self) -> None:
        if self.state.text_input_cursor > 0:
            self.state.text_input_cursor -= 1

    def move_cursor_right(self) -> None:
        if self.state.text_input_cursor < len(self.state.text_input_buffer):
            self.state.text_input_cursor += 1

    def _reset_text_input(self) -> None:
        self.state.text_input_buffer = ""
        self.state.text_input_cursor = 0
        self.state.text_input_mode = None

    # ===== OPERATION MANAGEMENT =====

    def submit_modify(self) -> None:
        from ...core.debug import is_debug_enabled, debug_print

        if self.state.current_operation:
            self.state.current_operation.content = self.state.text_input_buffer
            self.state.operations_modified = True
            if is_debug_enabled():
                debug_print(
                    f"Content modified: {self.state.text_input_buffer[:50]}...", "DIFF"
                )

        self.state.mode = DiffReviewMode.MENU
        self._reset_text_input()

    def submit_prompt(self) -> None:
        if self.state.current_operation:
            self.state.current_operation.prompt_instruction = (
                self.state.text_input_buffer
            )

        self.state.mode = DiffReviewMode.PROMPT_PROCESSING
        self.state.prompt_error = None
        self._reset_text_input()

    def set_prompt_error(self, error: str | None) -> None:
        self.state.prompt_error = error

    def mark_modified(self) -> None:
        self.state.operations_modified = True

    def advance_to_next(self) -> None:
        self.state.current_index += 1

    # ===== MENU NAVIGATION =====

    def move_selection_up(self, num_options: int) -> None:
        self.state.selected = (self.state.selected - 1) % num_options

    def move_selection_down(self, num_options: int) -> None:
        self.state.selected = (self.state.selected + 1) % num_options


# ===== AI PROCESSING =====


class DiffAIProcessor:
    # AI callback orchestration for interactive diff review UI.

    def __init__(
        self,
        state: "DiffState",
        state_manager: "DiffStateManager",
        ai_context: "AIContext",
        callback: PromptCallback | None,
        renderer: "DiffRenderer",
    ):
        self.state = state
        self.manager = state_manager
        self.context = ai_context
        self.callback = callback
        self.renderer = renderer

    def process_prompt(self, live: "Live") -> None:
        from ...core.exceptions import AIError, EditError
        from ...core.debug import is_debug_enabled, debug_print
        from ...loom_io.console import console

        # force refresh loading screen
        live.update(self.renderer.render_screen(self.state))
        live.refresh()

        loading_start_time = time.time()
        if is_debug_enabled():
            debug_print(
                f"Starting AI processing at {time.strftime('%H:%M:%S')}...", "DIFF"
            )

        # small delay to ensure loading screen displays
        time.sleep(0.1)

        # check required contexts
        if not self._validate_context():
            self._ensure_min_loading_time(loading_start_time)
            live.update(self.renderer.render_screen(self.state))
            return

        # check callback exists
        if not self.callback:
            self.manager.set_prompt_error("Prompt regeneration not configured")
            self._ensure_min_loading_time(loading_start_time)
            live.update(self.renderer.render_screen(self.state))
            return

        # call callback
        ai_start_time = time.time()
        if is_debug_enabled():
            debug_print(f"Calling AI model '{self.context.model}'...", "DIFF")

        # type narrowing: _validate_context() ensures these are not None
        assert self.state.current_operation is not None
        assert self.context.resume_lines is not None
        assert self.context.job_text is not None
        assert self.context.model is not None

        try:
            success = self.callback(
                self.state.current_operation,
                self.context.resume_lines,
                self.context.job_text,
                self.context.sections_json,
                self.context.model,
            )

            ai_duration = time.time() - ai_start_time
            if is_debug_enabled():
                debug_print(f"AI call completed in {ai_duration:.2f} seconds", "DIFF")

            self._ensure_min_loading_time(loading_start_time)

            if success:
                self.manager.mark_modified()
                console.print("[green]AI regenerated the edit based on your prompt[/]")
                self.manager.return_to_menu()
            else:
                self.manager.set_prompt_error("AI processing failed")
                live.update(self.renderer.render_screen(self.state))

        except (AIError, EditError) as e:
            self.manager.set_prompt_error(str(e))
            console.print(f"[red]AI Error: {e}[/]")
            self._ensure_min_loading_time(loading_start_time)
            live.update(self.renderer.render_screen(self.state))
        except Exception as e:
            self.manager.set_prompt_error(f"Unexpected error: {str(e)}")
            console.print(f"[red]Unexpected Error: {e}[/]")
            self._ensure_min_loading_time(loading_start_time)
            live.update(self.renderer.render_screen(self.state))

    def _validate_context(self) -> bool:
        if (
            self.context.resume_lines is None
            or self.context.job_text is None
            or self.context.model is None
        ):
            self.manager.set_prompt_error(
                "Missing required context for AI processing (resume, job, or model)"
            )
            return False
        return True

    def _ensure_min_loading_time(self, start_time: float) -> None:
        from ...core.debug import is_debug_enabled, debug_print

        elapsed = time.time() - start_time
        if elapsed < MIN_LOADING_DURATION:
            remaining = MIN_LOADING_DURATION - elapsed
            if is_debug_enabled():
                debug_print(
                    f"Ensuring minimum loading duration... {remaining:.1f}s remaining",
                    "DIFF",
                )
            time.sleep(remaining)


def get_default_prompt_callback() -> PromptCallback:
    # return the default prompt callback for AI regeneration
    return _default_prompt_callback


def _default_prompt_callback(
    operation: "EditOperation",
    resume_lines: "Lines",
    job_text: str,
    sections_json: str | None,
    model: str,
) -> bool:
    # Default callback that uses pipeline.process_prompt_operation.
    # ! import here to avoid tight coupling at module level
    from ...core.pipeline import process_prompt_operation
    from ...core.exceptions import AIError, EditError
    from ...core.debug import is_debug_enabled, debug_print
    from ...loom_io.console import console

    try:
        prompt_preview = operation.prompt_instruction or "(empty)"
        if is_debug_enabled():
            debug_print(
                f"Processing prompt: '{prompt_preview[:50]}{'...' if len(prompt_preview) > 50 else ''}'",
                "DIFF",
            )

        updated_operation = process_prompt_operation(
            operation, resume_lines, job_text, sections_json, model
        )

        # update operation in-place
        operation.content = updated_operation.content
        operation.reasoning = updated_operation.reasoning
        operation.confidence = updated_operation.confidence
        operation.prompt_instruction = None

        if is_debug_enabled():
            debug_print(
                f"AI generated {len(operation.content)} characters of new content",
                "DIFF",
            )
        return True

    except (AIError, EditError) as e:
        console.print(f"[red]AI Error: {e}[/]")
        raise
    except Exception as e:
        console.print(f"[red]Unexpected Error: {e}[/]")
        raise
