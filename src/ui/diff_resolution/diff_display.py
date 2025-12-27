# src/ui/diff_resolution/diff_display.py
# Interactive diff display interface w/ rich UI components for edit operation review

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from ..core.rich_components import Live, RenderableType, Text
from readchar import readkey, key

from .diff_state import (
    DiffState,
    DiffStateManager,
    DiffReviewMode,
    AIContext,
    DiffAIProcessor,
    PromptCallback,
    get_default_prompt_callback,
)
from .diff_renderer import DiffRenderer, OPTIONS, MIN_W, MAX_W, MIN_H, MAX_H, _clamp
from .diff_input import DiffInputHandler

if TYPE_CHECKING:
    from ...loom_io.types import Lines
    from ...core.constants import EditOperation

from ...loom_io.console import console

FIXED_W = _clamp(console.size.width // 2, MIN_W, MAX_W)
FIXED_H = _clamp(console.size.height // 2, MIN_H, MAX_H)


# * Orchestrates interactive diff review session
# * Coordinates state, rendering, input handling & AI processing components
# * Exposes stable component accessors for extensibility; internal state via self.state
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

    # ===== STABLE COMPONENT ACCESSORS (read-only) =====
    # Use these for advanced customization; prefer public API for typical use

    @property
    def state(self) -> DiffState:
        # Access to diff state (read-only accessor).
        return self._state

    @property
    def renderer(self) -> DiffRenderer:
        # Access to renderer (read-only accessor).
        return self._renderer

    @property
    def input_handler(self) -> DiffInputHandler:
        # Access to input handler (read-only accessor).
        return self._input_handler

    @property
    def ai_processor(self) -> DiffAIProcessor:
        # Access to AI processor (read-only accessor).
        return self._ai_processor

    # ===== INTENTIONAL PUBLIC API =====

    @property
    def operations(self) -> list["EditOperation"]:
        # Operations list - primary data access.
        return self._state.operations

    @property
    def is_complete(self) -> bool:
        # Whether the review session is complete.
        return self._state.is_complete

    def render_screen(self) -> RenderableType:
        # Render the current screen state.
        return self._renderer.render_screen(self._state)

    def handle_key(self, k: str) -> bool:
        # Handle keyboard input. Returns False to exit loop.
        return self._input_handler.handle_key(k)

    def get_result(self) -> tuple[list["EditOperation"], bool]:
        # Get final result: (operations, were_modified).
        return self._state.operations, self._state.operations_modified

    def run(self) -> tuple[list["EditOperation"], bool]:
        # Run the interactive review session. Returns (operations, were_modified).
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
