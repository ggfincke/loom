# src/ui/diff_resolution/diff_state.py
# State management for interactive diff review UI

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...loom_io.types import Lines
    from ...core.constants import EditOperation


# UI state enum for mode transitions
class DiffReviewMode(Enum):
    MENU = "menu"
    TEXT_INPUT = "text_input"
    PROMPT_PROCESSING = "processing"


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
