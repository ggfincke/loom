# src/ui/diff_resolution/diff_renderer.py
# Rendering components for interactive diff review UI

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..core.rich_components import (
    Layout,
    Panel,
    Text,
    Align,
    RenderableType,
    Table,
    Padding,
    Spinner,
    Columns,
)

if TYPE_CHECKING:
    from .diff_state import DiffState, DiffReviewMode
    from ...core.constants import EditOperation, DiffOp


# menu options
OPTIONS = [
    "Approve",
    "Reject",
    "Skip",
    "Modify",
    "Prompt",
    "Exit",
]

MIN_W, MAX_W = 60, 120
MIN_H, MAX_H = 25, 25


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


@dataclass
class RenderDimensions:

    width: int
    height: int


class DiffRenderer:

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    # ===== OPERATION DISPLAY =====

    def render_operation_display(self, edit_op: "EditOperation | None") -> list[Text]:
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
                Text(
                    f"- Delete lines {edit_op.start_line}-{edit_op.end_line}",
                    style="red",
                )
            )

        # display reasoning if available
        if edit_op.reasoning:
            lines.append(Text(""))
            lines.append(Text("Reasoning:", style="bold"))
            lines.append(Text(edit_op.reasoning, style="dim"))

        return lines

    # ===== TEXT INPUT DISPLAY =====

    def render_text_input_display(self, state: "DiffState") -> list[Text]:
        lines: list[Text] = []

        # header
        if state.text_input_mode == "modify":
            lines.append(Text("MODIFY OPERATION", style="bold yellow"))
            lines.append(Text("Edit the suggested content below:", style="dim"))
        elif state.text_input_mode == "prompt":
            lines.append(Text("PROMPT LLM", style="bold cyan"))
            lines.append(
                Text("Enter additional instructions for the LLM:", style="dim")
            )

        lines.append(Text(""))

        # current op context (unchanged)
        if state.current_operation:
            lines.append(Text("Current content:", style="bold"))
            preview = (
                state.current_operation.content[:100] + "..."
                if len(state.current_operation.content) > 100
                else state.current_operation.content
            )
            lines.append(Text(preview, style="dim"))
            lines.append(Text(""))

        # prompt label
        lines.append(Text("Your input:", style="bold"))

        # terminal-like single line input (no panel/box)
        cursor_char = "|"
        display_text = (
            state.text_input_buffer[: state.text_input_cursor]
            + cursor_char
            + state.text_input_buffer[state.text_input_cursor :]
        )

        # best-effort trimming to visible frame width
        frame_w = max(20, self.width - 6)
        if len(display_text) > frame_w - 2:
            display_text = "..." + display_text[-(frame_w - 3) :]

        lines.append(Text("> " + display_text))

        lines.append(Text(""))
        lines.append(
            Text("Press [Enter] to submit, [Esc] to cancel", style="dim italic")
        )
        return lines

    # ===== PROMPT LOADING DISPLAY =====

    def render_prompt_loading(self, state: "DiffState") -> RenderableType:
        from rich.console import Group

        lines: list[RenderableType] = []

        # header
        lines.append(Text("PROCESSING PROMPT", style="bold cyan"))
        lines.append(
            Text(
                "The AI is regenerating the edit based on your instructions...",
                style="dim",
            )
        )
        lines.append(Text(""))

        # show current operation context
        if state.current_operation:
            lines.append(Text("Processing operation:", style="bold"))
            lines.append(
                Text(
                    f"  {state.current_operation.operation} at line {state.current_operation.line_number}",
                    style="loom.accent2",
                )
            )
            if state.current_operation.prompt_instruction:
                instruction_preview = (
                    state.current_operation.prompt_instruction[:80] + "..."
                    if len(state.current_operation.prompt_instruction) > 80
                    else state.current_operation.prompt_instruction
                )
                lines.append(Text(f"  Instruction: {instruction_preview}", style="dim"))
            lines.append(Text(""))

        # loading indicator w/ animated spinner
        if not state.prompt_error:
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
            Text(
                "Please wait while the AI generates a new suggestion.",
                style="dim italic",
            )
        )
        lines.append(Text("Press [Esc] to cancel if needed.", style="dim italic"))

        # error display if present
        if state.prompt_error:
            lines.append(Text(""))
            lines.append(Text("Error occurred:", style="bold red"))
            lines.append(Text(str(state.prompt_error), style="red"))
            lines.append(Text(""))
            lines.append(
                Text("Press [Enter] to continue with original edit", style="dim italic")
            )

        return Group(*lines)

    # ===== HEADER/FOOTER =====

    def render_header(
        self, filename: str, current_index: int, total_ops: int
    ) -> RenderableType:
        current_num = min(current_index + 1, total_ops)

        left_text = Text(f"Reviewing: {filename}", style="bold loom.accent")
        right_text = Text(
            f"Suggestion {current_num} of {total_ops}", style="loom.accent2"
        )

        header_table = Table.grid(padding=0, expand=True)
        header_table.add_column(ratio=1, justify="left")
        header_table.add_column(no_wrap=True, justify="right")
        header_table.add_row(left_text, right_text)

        return Panel(header_table, border_style="dim", padding=(0, 1))

    def render_footer(
        self, operations: list["EditOperation"], current_index: int
    ) -> RenderableType:
        from ...core.constants import DiffOp

        approved = sum(
            1 for op in operations[:current_index] if op.status == DiffOp.APPROVE
        )
        rejected = sum(
            1 for op in operations[:current_index] if op.status == DiffOp.REJECT
        )
        skipped = sum(
            1 for op in operations[:current_index] if op.status == DiffOp.SKIP
        )

        summary_text = Text(
            f"Approved: {approved} | Rejected: {rejected} | Skipped: {skipped}",
            style="loom.accent2",
        )

        return Panel(Align.center(summary_text), border_style="dim", padding=(0, 1))

    # ===== BODY CONTENT ROUTING =====

    def get_body_content(self, state: "DiffState") -> RenderableType:
        from .diff_state import DiffReviewMode

        if state.mode == DiffReviewMode.PROMPT_PROCESSING:
            return self.render_prompt_loading(state)
        elif state.mode == DiffReviewMode.TEXT_INPUT:
            input_lines = self.render_text_input_display(state)
            return Text("\n").join(input_lines)
        else:
            op_lines = self.render_operation_display(state.current_operation)
            return Text("\n").join(op_lines)

    # ===== MAIN SCREEN LAYOUT =====

    def render_screen(self, state: "DiffState") -> RenderableType:
        # create main layout w/ 3 rows
        main_layout = Layout()
        main_layout.split_column(
            Layout(name="header", size=3),
            Layout(name="content", ratio=1),
            Layout(name="footer", size=3),
        )

        # create content area w/ menu & diff display
        content_layout = Layout()
        content_layout.split_row(
            Layout(name="menu", ratio=1), Layout(name="body", ratio=3)
        )

        # create left menu w/ selection highlighting
        row_gap = 1
        grid = Table.grid(padding=0)
        grid.add_column(no_wrap=True)

        for i, opt in enumerate(OPTIONS):
            is_sel = i == state.selected
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
        body_content = self.get_body_content(state)
        body_panel = Panel(
            body_content, title="Current Edit", border_style="loom.accent2"
        )

        content_layout["menu"].update(menu_panel)
        content_layout["body"].update(body_panel)

        # update all layout sections
        main_layout["header"].update(
            self.render_header(
                state.filename, state.current_index, len(state.operations)
            )
        )
        main_layout["content"].update(content_layout)
        main_layout["footer"].update(
            self.render_footer(state.operations, state.current_index)
        )

        outer = Panel(
            main_layout,
            border_style="loom.accent",
            width=self.width,
            height=self.height,
        )
        return Align.left(outer, vertical="top")


def create_renderer_from_console() -> DiffRenderer:
    from ...loom_io.console import console

    width = _clamp(console.size.width // 2, MIN_W, MAX_W)
    height = _clamp(console.size.height // 2, MIN_H, MAX_H)
    return DiffRenderer(width, height)
