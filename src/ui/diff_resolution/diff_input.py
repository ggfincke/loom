# src/ui/diff_resolution/diff_input.py
# Input handling for interactive diff review UI

from __future__ import annotations

from typing import TYPE_CHECKING

from readchar import key

from .diff_state import DiffState, DiffStateManager, DiffReviewMode, OPTIONS


class DiffInputHandler:

    def __init__(self, state: DiffState, state_manager: DiffStateManager):
        self.state = state
        self.manager = state_manager

    def handle_key(self, k: str) -> bool:
        if self.state.mode == DiffReviewMode.TEXT_INPUT:
            return self._handle_text_input_key(k)
        elif self.state.mode == DiffReviewMode.PROMPT_PROCESSING:
            return self._handle_prompt_processing_key(k)
        else:
            return self._handle_menu_key(k)

    def _handle_menu_key(self, k: str) -> bool:
        if k in (key.UP, "k"):
            self.manager.move_selection_up(len(OPTIONS))
        elif k in (key.DOWN, "j"):
            self.manager.move_selection_down(len(OPTIONS))
        elif k == key.ENTER:
            return self._process_menu_selection()
        elif k in (key.ESC, key.CTRL_C):
            raise SystemExit
        return True

    def _handle_text_input_key(self, k: str) -> bool:
        if k == key.ESC:
            self.manager.cancel_text_input()
        elif k == key.ENTER:
            self._submit_text_input()
        elif k == key.BACKSPACE:
            self.manager.delete_before_cursor()
        elif k == key.LEFT:
            self.manager.move_cursor_left()
        elif k == key.RIGHT:
            self.manager.move_cursor_right()
        elif len(k) == 1 and k.isprintable():
            self.manager.insert_char(k)
        return True

    def _handle_prompt_processing_key(self, k: str) -> bool:
        if k == key.ENTER and self.state.prompt_error:
            # user acknowledged error, continue w/ original edit
            self.manager.return_to_menu()
        elif k in (key.ESC, key.CTRL_C):
            # cancel prompt processing
            self.manager.return_to_menu()
        return True

    def _process_menu_selection(self) -> bool:
        from ...core.constants import DiffOp

        selected_option = OPTIONS[self.state.selected]

        if selected_option == "Exit":
            return False

        if not self.state.current_operation:
            return False

        if selected_option == "Approve":
            self.state.current_operation.status = DiffOp.APPROVE
            self.manager.advance_to_next()
        elif selected_option == "Reject":
            self.state.current_operation.status = DiffOp.REJECT
            self.manager.advance_to_next()
        elif selected_option == "Skip":
            self.state.current_operation.status = DiffOp.SKIP
            self.manager.advance_to_next()
        elif selected_option == "Modify":
            self.manager.enter_modify_mode()
        elif selected_option == "Prompt":
            self.manager.enter_prompt_mode()

        return True

    def _submit_text_input(self) -> None:
        if self.state.text_input_mode == "modify":
            self.manager.submit_modify()
        elif self.state.text_input_mode == "prompt":
            self.manager.submit_prompt()
