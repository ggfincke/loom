# src/ui/diff_resolution/diff_display.py
# Interactive diff display interface w/ rich UI components for edit operation review

from __future__ import annotations

from enum import Enum
from typing import Callable

from ..core.rich_components import (
    Layout,
    Panel,
    Text,
    Live,
    Align,
    RenderableType,
    Table,
    Padding,
    Spinner,
    Columns,
)
from readchar import readkey, key
from ...loom_io.console import console
from ...loom_io.types import Lines
from ...core.constants import DiffOp, EditOperation
from ...core.exceptions import AIError, EditError
from ...core.debug import is_debug_enabled, debug_print


# UI state enum for mode transitions
class DiffReviewMode(Enum):
    MENU = "menu"
    TEXT_INPUT = "text_input"
    PROMPT_PROCESSING = "processing"


# menu options
OPTIONS = [
    DiffOp.APPROVE.value.capitalize(),
    DiffOp.REJECT.value.capitalize(),
    DiffOp.SKIP.value.capitalize(),
    DiffOp.MODIFY.value.capitalize(),
    DiffOp.PROMPT.value.capitalize(),
    "Exit",
]

MIN_W, MAX_W = 60, 120
MIN_H, MAX_H = 25, 25


# clamp value between min & max bounds
def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


# compute dimensions once
FIXED_W = _clamp(console.size.width // 2, MIN_W, MAX_W)
FIXED_H = _clamp(console.size.height // 2, MIN_H, MAX_H)


# type alias for prompt regeneration callback
PromptCallback = Callable[[EditOperation, Lines, str, str | None, str], bool]


# * Encapsulates state & rendering for interactive diff review UI
class InteractiveDiffResolver:
    def __init__(
        self,
        operations: list[EditOperation],
        filename: str = "document.txt",
        resume_lines: Lines | None = None,
        job_text: str | None = None,
        sections_json: str | None = None,
        model: str | None = None,
        on_prompt_regenerate: PromptCallback | None = None,
    ):
        # operation tracking
        self.operations = operations
        self.filename = filename
        self.current_index = 0

        # menu selection
        self.selected = 0

        # mode state (replaces multiple boolean flags)
        self.mode = DiffReviewMode.MENU

        # text input state
        self.text_input_buffer = ""
        self.text_input_cursor = 0
        self.text_input_mode: str | None = None  # "modify" or "prompt"

        # prompt processing state
        self.prompt_error: str | None = None

        # AI context for prompt operations
        self.ai_context = {
            "resume_lines": resume_lines,
            "job_text": job_text,
            "sections_json": sections_json,
            "model": model,
        }

        # callback for AI prompt regeneration
        self.on_prompt_regenerate = on_prompt_regenerate

        # track modifications during review
        self.operations_modified = False

    # get current operation being reviewed
    @property
    def current_operation(self) -> EditOperation | None:
        if 0 <= self.current_index < len(self.operations):
            return self.operations[self.current_index]
        return None

    # check if all operations have been reviewed
    @property
    def is_complete(self) -> bool:
        return self.current_index >= len(self.operations)

    # ===== DISPLAY METHODS =====

    # convert current EditOperation to display format
    def _render_operation_display(self) -> list[Text]:
        edit_op = self.current_operation
        if edit_op is None:
            return [Text("No edit operation selected", style="dim")]

        lines = []

        # display operation header
        lines.append(Text(f"Operation: {edit_op.operation}", style="bold loom.accent"))
        lines.append(Text(f"Line: {edit_op.line_number}", style="loom.accent2"))
        if edit_op.confidence > 0:
            lines.append(
                Text(f"Confidence: {edit_op.confidence:.2f}", style="loom.accent2")
            )
        lines.append(Text(""))

        # render operation-specific details
        if edit_op.operation == "replace_line":
            original = (
                edit_op.original_content if edit_op.original_content else "[no content]"
            )
            lines.append(Text(f"- Line {edit_op.line_number}: {original}", style="red"))
            lines.append(
                Text(f"+ Line {edit_op.line_number}: {edit_op.content}", style="green")
            )
        elif edit_op.operation == "replace_range":
            original = (
                edit_op.original_content if edit_op.original_content else "[no content]"
            )
            lines.append(
                Text(
                    f"- Lines {edit_op.start_line}-{edit_op.end_line}: {original}",
                    style="red",
                )
            )
            lines.append(
                Text(
                    f"+ Lines {edit_op.start_line}-{edit_op.end_line}: {edit_op.content}",
                    style="green",
                )
            )
        elif edit_op.operation == "insert_after":
            lines.append(
                Text(f"Insert after line {edit_op.line_number}:", style="loom.accent2")
            )
            lines.append(Text(f"+ {edit_op.content}", style="green"))
        elif edit_op.operation == "delete_range":
            lines.append(
                Text(f"- Delete lines {edit_op.start_line}-{edit_op.end_line}", style="red")
            )

        # display reasoning if available
        if edit_op.reasoning:
            lines.append(Text(""))
            lines.append(Text("Reasoning:", style="bold"))
            lines.append(Text(edit_op.reasoning, style="dim"))

        return lines

    # create text input display for MODIFY or PROMPT modes
    def _render_text_input_display(self) -> list[Text]:
        lines: list[Text] = []

        # header
        if self.text_input_mode == "modify":
            lines.append(Text("MODIFY OPERATION", style="bold yellow"))
            lines.append(Text("Edit the suggested content below:", style="dim"))
        elif self.text_input_mode == "prompt":
            lines.append(Text("PROMPT LLM", style="bold cyan"))
            lines.append(Text("Enter additional instructions for the LLM:", style="dim"))

        lines.append(Text(""))

        # current op context (unchanged)
        if self.current_operation:
            lines.append(Text("Current content:", style="bold"))
            preview = (
                self.current_operation.content[:100] + "..."
                if len(self.current_operation.content) > 100
                else self.current_operation.content
            )
            lines.append(Text(preview, style="dim"))
            lines.append(Text(""))

        # prompt label
        lines.append(Text("Your input:", style="bold"))

        # terminal-like single line input (no panel/box)
        cursor_char = "|" if self.text_input_cursor == len(self.text_input_buffer) else "|"
        display_text = (
            self.text_input_buffer[: self.text_input_cursor]
            + cursor_char
            + self.text_input_buffer[self.text_input_cursor :]
        )

        # best-effort trimming to visible frame width
        frame_w = max(20, FIXED_W - 6)
        if len(display_text) > frame_w - 2:
            display_text = "..." + display_text[-(frame_w - 3) :]

        lines.append(Text("> " + display_text))

        lines.append(Text(""))
        lines.append(Text("Press [Enter] to submit, [Esc] to cancel", style="dim italic"))
        return lines

    # create loading display for prompt processing
    def _render_prompt_loading(self) -> RenderableType:
        from rich.console import Group

        lines: list[RenderableType] = []

        # header
        lines.append(Text("PROCESSING PROMPT", style="bold cyan"))
        lines.append(
            Text(
                "The AI is regenerating the edit based on your instructions...", style="dim"
            )
        )
        lines.append(Text(""))

        # show current operation context
        if self.current_operation:
            lines.append(Text("Processing operation:", style="bold"))
            lines.append(
                Text(
                    f"  {self.current_operation.operation} at line {self.current_operation.line_number}",
                    style="loom.accent2",
                )
            )
            if self.current_operation.prompt_instruction:
                instruction_preview = (
                    self.current_operation.prompt_instruction[:80] + "..."
                    if len(self.current_operation.prompt_instruction) > 80
                    else self.current_operation.prompt_instruction
                )
                lines.append(Text(f"  Instruction: {instruction_preview}", style="dim"))
            lines.append(Text(""))

        # loading indicator w/ animated spinner
        if not self.prompt_error:
            spinner_line = Columns(
                [
                    Spinner("dots", style="cyan"),
                    Text(" Processing... This may take several seconds.", style="cyan"),
                ]
            )
            lines.append(Text(""))
            lines.append(spinner_line)
        else:
            lines.append(Text("Processing...", style="cyan"))

        lines.append(Text(""))
        lines.append(
            Text("Please wait while the AI generates a new suggestion.", style="dim italic")
        )
        lines.append(Text("Press [Esc] to cancel if needed.", style="dim italic"))

        # error display if present
        if self.prompt_error:
            lines.append(Text(""))
            lines.append(Text("Error occurred:", style="bold red"))
            lines.append(Text(str(self.prompt_error), style="red"))
            lines.append(Text(""))
            lines.append(
                Text("Press [Enter] to continue with original edit", style="dim italic")
            )

        return Group(*lines)

    # create header layout w/ filename & progress info
    def _render_header(self) -> RenderableType:
        total_ops = len(self.operations)
        current_num = min(self.current_index + 1, total_ops)

        left_text = Text(f"Reviewing: {self.filename}", style="bold loom.accent")
        right_text = Text(f"Suggestion {current_num} of {total_ops}", style="loom.accent2")

        header_table = Table.grid(padding=0, expand=True)
        header_table.add_column(ratio=1, justify="left")
        header_table.add_column(no_wrap=True, justify="right")
        header_table.add_row(left_text, right_text)

        return Panel(header_table, border_style="dim", padding=(0, 1))

    # create footer layout w/ approval/rejection/skip counts
    def _render_footer(self) -> RenderableType:
        approved = sum(
            1
            for op in self.operations[: self.current_index]
            if op.status == DiffOp.APPROVE
        )
        rejected = sum(
            1
            for op in self.operations[: self.current_index]
            if op.status == DiffOp.REJECT
        )
        skipped = sum(
            1
            for op in self.operations[: self.current_index]
            if op.status == DiffOp.SKIP
        )

        summary_text = Text(
            f"Approved: {approved} | Rejected: {rejected} | Skipped: {skipped}",
            style="loom.accent2",
        )

        return Panel(Align.center(summary_text), border_style="dim", padding=(0, 1))

    # get dynamic content based on current mode
    def _get_body_content(self) -> RenderableType:
        if self.mode == DiffReviewMode.PROMPT_PROCESSING:
            return self._render_prompt_loading()
        elif self.mode == DiffReviewMode.TEXT_INPUT:
            input_lines = self._render_text_input_display()
            return Text("\n").join(input_lines)
        else:
            op_lines = self._render_operation_display()
            return Text("\n").join(op_lines)

    # render main screen layout
    def render_screen(self) -> RenderableType:
        # create main layout w/ 3 rows
        main_layout = Layout()
        main_layout.split_column(
            Layout(name="header", size=3),
            Layout(name="content", ratio=1),
            Layout(name="footer", size=3),
        )

        # create content area w/ menu & diff display
        content_layout = Layout()
        content_layout.split_row(Layout(name="menu", ratio=1), Layout(name="body", ratio=3))

        # create left menu w/ selection highlighting
        row_gap = 1
        grid = Table.grid(padding=0)
        grid.add_column(no_wrap=True)

        for i, opt in enumerate(OPTIONS):
            is_sel = i == self.selected
            prefix = "> " if is_sel else "  "
            style = "reverse bold loom.accent" if is_sel else "loom.accent2"
            cell = Text(prefix + opt, style=style)
            bottom = row_gap if i < len(OPTIONS) - 1 else 0
            grid.add_row(Padding(cell, (0, 0, bottom, 0)))

        menu_panel = Panel(
            Align.center(grid, vertical="top"),
            title="Options",
            border_style="loom.accent2",
            padding=(1, 2),
        )

        # create right diff pane w/ operation details
        body_content = self._get_body_content()
        body_panel = Panel(body_content, title="Current Edit", border_style="loom.accent2")

        content_layout["menu"].update(menu_panel)
        content_layout["body"].update(body_panel)

        # update all layout sections
        main_layout["header"].update(self._render_header())
        main_layout["content"].update(content_layout)
        main_layout["footer"].update(self._render_footer())

        outer = Panel(
            main_layout, border_style="loom.accent", width=FIXED_W, height=FIXED_H
        )
        return Align.left(outer, vertical="top")

    # ===== KEY HANDLERS =====

    # process keyboard input; returns True to continue, False to exit
    def handle_key(self, k: str) -> bool:
        if self.mode == DiffReviewMode.TEXT_INPUT:
            return self._handle_text_input_key(k)
        elif self.mode == DiffReviewMode.PROMPT_PROCESSING:
            return self._handle_prompt_processing_key(k)
        else:
            return self._handle_menu_key(k)

    # handle key input in menu mode
    def _handle_menu_key(self, k: str) -> bool:
        if k in (key.UP, "k"):
            self.selected = (self.selected - 1) % len(OPTIONS)
        elif k in (key.DOWN, "j"):
            self.selected = (self.selected + 1) % len(OPTIONS)
        elif k == key.ENTER:
            return self._process_menu_selection()
        elif k in (key.ESC, key.CTRL_C):
            raise SystemExit
        return True

    # handle key input in text input mode
    def _handle_text_input_key(self, k: str) -> bool:
        if k == key.ESC:
            self._cancel_text_input()
        elif k == key.ENTER:
            self._submit_text_input()
        elif k == key.BACKSPACE:
            if self.text_input_cursor > 0:
                self.text_input_buffer = (
                    self.text_input_buffer[: self.text_input_cursor - 1]
                    + self.text_input_buffer[self.text_input_cursor :]
                )
                self.text_input_cursor -= 1
        elif k == key.LEFT:
            if self.text_input_cursor > 0:
                self.text_input_cursor -= 1
        elif k == key.RIGHT:
            if self.text_input_cursor < len(self.text_input_buffer):
                self.text_input_cursor += 1
        elif len(k) == 1 and k.isprintable():
            self.text_input_buffer = (
                self.text_input_buffer[: self.text_input_cursor]
                + k
                + self.text_input_buffer[self.text_input_cursor :]
            )
            self.text_input_cursor += 1
        return True

    # handle key input during prompt processing
    def _handle_prompt_processing_key(self, k: str) -> bool:
        if k == key.ENTER and self.prompt_error:
            # user acknowledged error, continue w/ original edit
            self.mode = DiffReviewMode.MENU
            self.prompt_error = None
        elif k in (key.ESC, key.CTRL_C):
            # cancel prompt processing
            self.mode = DiffReviewMode.MENU
            self.prompt_error = None
        return True

    # ===== OPERATION ACTIONS =====

    # process user's menu selection; returns False to exit loop
    def _process_menu_selection(self) -> bool:
        selected_option = OPTIONS[self.selected]

        if selected_option == "Exit":
            return False

        if not self.current_operation:
            return False

        if selected_option == "Approve":
            self.current_operation.status = DiffOp.APPROVE
            self._advance_to_next()
        elif selected_option == "Reject":
            self.current_operation.status = DiffOp.REJECT
            self._advance_to_next()
        elif selected_option == "Skip":
            self.current_operation.status = DiffOp.SKIP
            self._advance_to_next()
        elif selected_option == "Modify":
            self._enter_modify_mode()
        elif selected_option == "Prompt":
            self._enter_prompt_mode()

        return True

    # enter text editing mode for current operation
    def _enter_modify_mode(self) -> None:
        if self.current_operation:
            self.mode = DiffReviewMode.TEXT_INPUT
            self.text_input_mode = "modify"
            self.text_input_buffer = self.current_operation.content
            self.text_input_cursor = len(self.text_input_buffer)

    # enter prompt entry mode
    def _enter_prompt_mode(self) -> None:
        self.mode = DiffReviewMode.TEXT_INPUT
        self.text_input_mode = "prompt"
        self.text_input_buffer = ""
        self.text_input_cursor = 0

    # cancel text input & return to menu
    def _cancel_text_input(self) -> None:
        self.mode = DiffReviewMode.MENU
        self.text_input_buffer = ""
        self.text_input_cursor = 0
        self.text_input_mode = None
        self.prompt_error = None

    # submit text input (MODIFY or PROMPT)
    def _submit_text_input(self) -> None:
        if self.text_input_mode == "modify":
            self._submit_modify()
        elif self.text_input_mode == "prompt":
            self._submit_prompt()

    # submit modified content
    def _submit_modify(self) -> None:
        if self.current_operation:
            self.current_operation.content = self.text_input_buffer
            self.operations_modified = True
            if is_debug_enabled():
                debug_print(
                    f"Content modified: {self.text_input_buffer[:50]}...", "DIFF"
                )

        # reset state and return to menu
        self.mode = DiffReviewMode.MENU
        self.text_input_buffer = ""
        self.text_input_cursor = 0
        self.text_input_mode = None

    # submit prompt for AI regeneration
    def _submit_prompt(self) -> None:
        if not self.current_operation:
            return

        # store prompt instruction
        self.current_operation.prompt_instruction = self.text_input_buffer

        # transition to processing mode
        self.mode = DiffReviewMode.PROMPT_PROCESSING
        self.prompt_error = None

        # reset text input state
        self.text_input_buffer = ""
        self.text_input_cursor = 0
        self.text_input_mode = None

    # process pending prompt via callback; called during main loop when in PROMPT_PROCESSING mode
    def process_prompt(self, live: Live) -> None:
        import time

        # force refresh loading screen
        live.update(self.render_screen())
        live.refresh()

        loading_start_time = time.time()
        if is_debug_enabled():
            debug_print(
                f"Starting AI processing at {time.strftime('%H:%M:%S')}...", "DIFF"
            )

        # small delay to ensure loading screen displays
        time.sleep(0.1)

        # check required contexts
        if (
            self.ai_context["resume_lines"] is None
            or self.ai_context["job_text"] is None
            or self.ai_context["model"] is None
        ):
            self.prompt_error = "Missing required context for AI processing (resume, job, or model)"
            self._ensure_min_loading_time(loading_start_time, 1.5)
            live.update(self.render_screen())
            return

        # check callback exists
        if not self.on_prompt_regenerate:
            self.prompt_error = "Prompt regeneration not configured"
            self._ensure_min_loading_time(loading_start_time, 1.5)
            live.update(self.render_screen())
            return

        # call callback
        ai_start_time = time.time()
        if is_debug_enabled():
            debug_print(
                f"Calling AI model '{self.ai_context['model']}'...", "DIFF"
            )

        try:
            success = self.on_prompt_regenerate(
                self.current_operation,
                self.ai_context["resume_lines"],
                self.ai_context["job_text"],
                self.ai_context["sections_json"],
                self.ai_context["model"],
            )

            ai_duration = time.time() - ai_start_time
            if is_debug_enabled():
                debug_print(f"AI call completed in {ai_duration:.2f} seconds", "DIFF")

            self._ensure_min_loading_time(loading_start_time, 1.5)

            if success:
                self.operations_modified = True
                console.print("[green]AI regenerated the edit based on your prompt[/]")
                self.mode = DiffReviewMode.MENU
            else:
                self.prompt_error = "AI processing failed"
                live.update(self.render_screen())

        except (AIError, EditError) as e:
            self.prompt_error = str(e)
            console.print(f"[red]AI Error: {e}[/]")
            self._ensure_min_loading_time(loading_start_time, 1.5)
            live.update(self.render_screen())
        except Exception as e:
            self.prompt_error = f"Unexpected error: {str(e)}"
            console.print(f"[red]Unexpected Error: {e}[/]")
            self._ensure_min_loading_time(loading_start_time, 1.5)
            live.update(self.render_screen())

    # ensure minimum loading screen duration
    def _ensure_min_loading_time(self, start_time: float, min_duration: float) -> None:
        import time

        elapsed = time.time() - start_time
        if elapsed < min_duration:
            remaining = min_duration - elapsed
            if is_debug_enabled():
                debug_print(
                    f"Ensuring minimum loading duration... {remaining:.1f}s remaining",
                    "DIFF",
                )
            time.sleep(remaining)

    # move to next operation
    def _advance_to_next(self) -> None:
        self.current_index += 1

    # return reviewed operations & modification flag
    def get_result(self) -> tuple[list[EditOperation], bool]:
        return self.operations, self.operations_modified

    # ===== MAIN LOOP =====

    # run the interactive diff review loop; returns (operations, was_modified)
    def run(self) -> tuple[list[EditOperation], bool]:
        # track if we just submitted a prompt
        prompt_just_submitted = False

        with Live(
            self.render_screen(), console=console, screen=True, refresh_per_second=30
        ) as live:
            while not self.is_complete:
                # if in prompt processing mode, process the prompt
                if self.mode == DiffReviewMode.PROMPT_PROCESSING and prompt_just_submitted:
                    prompt_just_submitted = False
                    self.process_prompt(live)
                    live.update(self.render_screen())
                    continue

                k = readkey()

                # track if we're about to submit a prompt
                if (
                    self.mode == DiffReviewMode.TEXT_INPUT
                    and self.text_input_mode == "prompt"
                    and k == key.ENTER
                ):
                    prompt_just_submitted = True

                # process key
                should_continue = self.handle_key(k)

                if not should_continue:
                    break

                # update display
                live.update(self.render_screen())

        return self.get_result()


# * Default callback for prompt regeneration - wraps core.pipeline.process_prompt_operation
def _default_prompt_callback(
    operation: EditOperation,
    resume_lines: Lines,
    job_text: str,
    sections_json: str | None,
    model: str,
) -> bool:
    # ! import here to avoid tight coupling at module level
    from ...core.pipeline import process_prompt_operation

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


# * Interactive diff review loop - thin wrapper for backwards compatibility
def main_display_loop(
    operations: list[EditOperation] | None = None,
    filename: str = "document.txt",
    resume_lines: Lines | None = None,
    job_text: str | None = None,
    sections_json: str | None = None,
    model: str | None = None,
    on_prompt_regenerate: PromptCallback | None = None,
) -> tuple[list[EditOperation], bool]:
    # use default callback if not provided
    callback = on_prompt_regenerate or _default_prompt_callback

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


# execute main loop when run directly
if __name__ == "__main__":
    main_display_loop()
