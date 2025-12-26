# src/ui/diff_resolution/diff_display.py
# Interactive diff display interface w/ rich UI components for edit operation review

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from ..core.rich_components import Live, RenderableType, Text
from readchar import readkey, key

from .diff_state import DiffState, DiffStateManager, DiffReviewMode, AIContext
from .diff_renderer import DiffRenderer, OPTIONS, MIN_W, MAX_W, MIN_H, MAX_H, _clamp
from .diff_input import DiffInputHandler
from .diff_ai_processor import (
    DiffAIProcessor,
    PromptCallback,
    get_default_prompt_callback,
)

if TYPE_CHECKING:
    from ...loom_io.types import Lines
    from ...core.constants import EditOperation

from ...loom_io.console import console

FIXED_W = _clamp(console.size.width // 2, MIN_W, MAX_W)
FIXED_H = _clamp(console.size.height // 2, MIN_H, MAX_H)


# orchestrates interactive diff review session; coordinates state, rendering, input handling & AI processing components
class InteractiveDiffResolver:
    def __init__(
        self,
        operations: list["EditOperation"],
        filename: str = "document.txt",
        resume_lines: "Lines | None" = None,
        job_text: str | None = None,
        sections_json: str | None = None,
        model: str | None = None,
        on_prompt_regenerate: PromptCallback | None = None,
    ):
        self._state = DiffState(operations=operations, filename=filename)
        self._state_manager = DiffStateManager(self._state)

        self._renderer = DiffRenderer(FIXED_W, FIXED_H)

        self._input_handler = DiffInputHandler(self._state, self._state_manager)

        ai_context = AIContext(
            resume_lines=resume_lines,
            job_text=job_text,
            sections_json=sections_json,
            model=model,
        )
        self._ai_processor = DiffAIProcessor(
            state=self._state,
            state_manager=self._state_manager,
            ai_context=ai_context,
            callback=on_prompt_regenerate,
            renderer=self._renderer,
        )

        self.on_prompt_regenerate = on_prompt_regenerate


    @property
    def operations(self) -> list["EditOperation"]:
        return self._state.operations

    @property
    def filename(self) -> str:
        return self._state.filename

    @property
    def current_index(self) -> int:
        return self._state.current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        self._state.current_index = value

    @property
    def selected(self) -> int:
        return self._state.selected

    @selected.setter
    def selected(self, value: int) -> None:
        self._state.selected = value

    @property
    def mode(self) -> DiffReviewMode:
        return self._state.mode

    @mode.setter
    def mode(self, value: DiffReviewMode) -> None:
        self._state.mode = value

    @property
    def text_input_buffer(self) -> str:
        return self._state.text_input_buffer

    @text_input_buffer.setter
    def text_input_buffer(self, value: str) -> None:
        self._state.text_input_buffer = value

    @property
    def text_input_cursor(self) -> int:
        return self._state.text_input_cursor

    @text_input_cursor.setter
    def text_input_cursor(self, value: int) -> None:
        self._state.text_input_cursor = value

    @property
    def text_input_mode(self) -> str | None:
        return self._state.text_input_mode

    @text_input_mode.setter
    def text_input_mode(self, value: str | None) -> None:
        self._state.text_input_mode = value

    @property
    def prompt_error(self) -> str | None:
        return self._state.prompt_error

    @prompt_error.setter
    def prompt_error(self, value: str | None) -> None:
        self._state.prompt_error = value

    @property
    def ai_context(self) -> dict:
        return {
            "resume_lines": self._ai_processor.context.resume_lines,
            "job_text": self._ai_processor.context.job_text,
            "sections_json": self._ai_processor.context.sections_json,
            "model": self._ai_processor.context.model,
        }

    @property
    def operations_modified(self) -> bool:
        return self._state.operations_modified

    @operations_modified.setter
    def operations_modified(self, value: bool) -> None:
        self._state.operations_modified = value

    @property
    def current_operation(self) -> "EditOperation | None":
        return self._state.current_operation

    @property
    def is_complete(self) -> bool:
        return self._state.is_complete


    def _render_operation_display(self) -> list[Text]:
        return self._renderer.render_operation_display(self._state.current_operation)

    def _render_text_input_display(self) -> list[Text]:
        return self._renderer.render_text_input_display(self._state)

    def _render_prompt_loading(self) -> RenderableType:
        return self._renderer.render_prompt_loading(self._state)

    def _render_header(self) -> RenderableType:
        return self._renderer.render_header(
            self._state.filename, self._state.current_index, len(self._state.operations)
        )

    def _render_footer(self) -> RenderableType:
        return self._renderer.render_footer(
            self._state.operations, self._state.current_index
        )

    def _get_body_content(self) -> RenderableType:
        return self._renderer.get_body_content(self._state)

    def render_screen(self) -> RenderableType:
        return self._renderer.render_screen(self._state)

    def handle_key(self, k: str) -> bool:
        return self._input_handler.handle_key(k)

    def _handle_menu_key(self, k: str) -> bool:
        return self._input_handler._handle_menu_key(k)

    def _handle_text_input_key(self, k: str) -> bool:
        return self._input_handler._handle_text_input_key(k)

    def _handle_prompt_processing_key(self, k: str) -> bool:
        return self._input_handler._handle_prompt_processing_key(k)

    def _process_menu_selection(self) -> bool:
        return self._input_handler._process_menu_selection()

    def _enter_modify_mode(self) -> None:
        self._state_manager.enter_modify_mode()

    def _enter_prompt_mode(self) -> None:
        self._state_manager.enter_prompt_mode()

    def _cancel_text_input(self) -> None:
        self._state_manager.cancel_text_input()

    def _submit_text_input(self) -> None:
        self._input_handler._submit_text_input()

    def _submit_modify(self) -> None:
        self._state_manager.submit_modify()

    def _submit_prompt(self) -> None:
        self._state_manager.submit_prompt()

    def process_prompt(self, live: Live) -> None:
        self._ai_processor.process_prompt(live)

    def _ensure_min_loading_time(self, start_time: float, min_duration: float) -> None:
        self._ai_processor._ensure_min_loading_time(start_time)

    def _advance_to_next(self) -> None:
        self._state_manager.advance_to_next()

    def get_result(self) -> tuple[list["EditOperation"], bool]:
        return self._state.operations, self._state.operations_modified


    def run(self) -> tuple[list["EditOperation"], bool]:
        prompt_just_submitted = False

        with Live(
            self.render_screen(), console=console, screen=True, refresh_per_second=30
        ) as live:
            while not self.is_complete:
                if (
                    self._state.mode == DiffReviewMode.PROMPT_PROCESSING
                    and prompt_just_submitted
                ):
                    prompt_just_submitted = False
                    self._ai_processor.process_prompt(live)
                    live.update(self.render_screen())
                    continue

                k = readkey()

                if (
                    self._state.mode == DiffReviewMode.TEXT_INPUT
                    and self._state.text_input_mode == "prompt"
                    and k == key.ENTER
                ):
                    prompt_just_submitted = True

                should_continue = self.handle_key(k)

                if not should_continue:
                    break

                live.update(self.render_screen())

        return self.get_result()




def _default_prompt_callback(
    operation: "EditOperation",
    resume_lines: "Lines",
    job_text: str,
    sections_json: str | None,
    model: str,
) -> bool:
    from .diff_ai_processor import _default_prompt_callback as _callback

    return _callback(operation, resume_lines, job_text, sections_json, model)


def main_display_loop(
    operations: list["EditOperation"] | None = None,
    filename: str = "document.txt",
    resume_lines: "Lines | None" = None,
    job_text: str | None = None,
    sections_json: str | None = None,
    model: str | None = None,
    on_prompt_regenerate: PromptCallback | None = None,
) -> tuple[list["EditOperation"], bool]:
    callback = on_prompt_regenerate or get_default_prompt_callback()

    resolver = InteractiveDiffResolver(
        operations=operations or [],
        filename=filename,
        resume_lines=resume_lines,
        job_text=job_text,
        sections_json=sections_json,
        model=model,
        on_prompt_regenerate=callback,
    )

    return resolver.run()


if __name__ == "__main__":
    main_display_loop()
