# src/ui/diff_resolution/diff_display.py
# Interactive diff display interface w/ rich UI components for edit operation review

from typing import Optional
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.console import RenderableType
from rich.table import Table
from rich.padding import Padding
from readchar import readkey, key
from ...loom_io.console import console
from ...core.constants import DiffOp, EditOperation

options = [DiffOp.APPROVE.value.capitalize(), DiffOp.REJECT.value.capitalize(), DiffOp.SKIP.value.capitalize(), DiffOp.MODIFY.value.capitalize(), DiffOp.PROMPT.value.capitalize(), "Exit"]
selected = 0

MIN_W, MAX_W = 60, 120
MIN_H, MAX_H = 25, 25

# * Clamp value between min & max bounds
def clamp(n, lo, hi): 
    return max(lo, min(hi, n))

# compute dimensions once
FIXED_W = clamp(console.size.width  // 2, MIN_W, MAX_W)
FIXED_H = clamp(console.size.height // 2, MIN_H, MAX_H)

# global state for current edit operation data
current_edit_operation = None
edit_operations = []
current_operation_index = 0
current_filename = "document.txt"

# text input state management
text_input_active = False
text_input_mode = None  # "modify" or "prompt"
text_input_buffer = ""
text_input_cursor = 0

# * Convert EditOperation to display format w/ styled text elements
def create_operation_display(edit_op: EditOperation | None) -> list[Text]:
    if edit_op is None:
        return [Text("No edit operation selected", style="dim")]
    
    lines = []
    
    # display operation header
    lines.append(Text(f"Operation: {edit_op.operation}", style="bold loom.accent"))
    lines.append(Text(f"Line: {edit_op.line_number}", style="loom.accent2"))
    if edit_op.confidence > 0:
        lines.append(Text(f"Confidence: {edit_op.confidence:.2f}", style="loom.accent2"))
    lines.append(Text(""))
    
    # render operation-specific details
    if edit_op.operation == "replace_line":
        original = edit_op.original_content if edit_op.original_content else "[no content]"
        lines.append(Text(f"- Line {edit_op.line_number}: {original}", style="red"))
        lines.append(Text(f"+ Line {edit_op.line_number}: {edit_op.content}", style="green"))
    elif edit_op.operation == "replace_range":
        original = edit_op.original_content if edit_op.original_content else "[no content]"
        lines.append(Text(f"- Lines {edit_op.start_line}-{edit_op.end_line}: {original}", style="red"))
        lines.append(Text(f"+ Lines {edit_op.start_line}-{edit_op.end_line}: {edit_op.content}", style="green"))
    elif edit_op.operation == "insert_after":
        lines.append(Text(f"Insert after line {edit_op.line_number}:", style="loom.accent2"))
        lines.append(Text(f"+ {edit_op.content}", style="green"))
    elif edit_op.operation == "delete_range":
        lines.append(Text(f"- Delete lines {edit_op.start_line}-{edit_op.end_line}", style="red"))
    
    # display reasoning if available
    if edit_op.reasoning:
        lines.append(Text(""))
        lines.append(Text("Reasoning:", style="bold"))
        lines.append(Text(edit_op.reasoning, style="dim"))
    
    return lines

# * Create text input display for MODIFY or PROMPT modes
def create_text_input_display(mode: str) -> list[Text]:
    lines: list[Text] = []

    # header
    if mode == "modify":
        lines.append(Text("✏️  MODIFY OPERATION", style="bold yellow"))
        lines.append(Text("Edit the suggested content below:", style="dim"))
    elif mode == "prompt":
        lines.append(Text("💬 PROMPT LLM", style="bold cyan"))
        lines.append(Text("Enter additional instructions for the LLM:", style="dim"))

    lines.append(Text(""))

    # current op context (unchanged)
    if current_edit_operation:
        lines.append(Text("Current content:", style="bold"))
        preview = (current_edit_operation.content[:100] + "…"
                   if len(current_edit_operation.content) > 100
                   else current_edit_operation.content)
        lines.append(Text(preview, style="dim"))
        lines.append(Text(""))

    # prompt label
    lines.append(Text("Your input:", style="bold"))

    # terminal-like single line input (no panel/box)
    cursor_char = "│" if text_input_cursor == len(text_input_buffer) else "▌"
    display_text = (
        text_input_buffer[:text_input_cursor] +
        cursor_char +
        text_input_buffer[text_input_cursor:]
    )

    # best-effort trimming to visible frame width
    frame_w = max(20, FIXED_W - 6)
    if len(display_text) > frame_w - 2:
        display_text = "…" + display_text[-(frame_w - 3):]

    lines.append(Text("> " + display_text))

    lines.append(Text(""))
    lines.append(Text("Press [Enter] to submit, [Esc] to cancel", style="dim italic"))
    return lines

# * Create header layout w/ filename & progress info
def create_header_layout() -> RenderableType:
    total_ops = len(edit_operations)
    current_num = min(current_operation_index + 1, total_ops)

    left_text  = Text(f"Reviewing: {current_filename}", style="bold loom.accent")
    right_text = Text(f"Suggestion {current_num} of {total_ops}", style="loom.accent2")

    # expand=True lets grid fill panel; left column takes remaining space
    header_table = Table.grid(padding=0, expand=True)
    header_table.add_column(ratio=1, justify="left")
    header_table.add_column(no_wrap=True, justify="right")
    header_table.add_row(left_text, right_text)

    return Panel(header_table, border_style="dim", padding=(0, 1))

# * Create footer layout w/ approval/rejection/skip counts
def create_footer_layout() -> RenderableType:
    approved = sum(1 for op in edit_operations[:current_operation_index] if op.status == DiffOp.APPROVE)
    rejected = sum(1 for op in edit_operations[:current_operation_index] if op.status == DiffOp.REJECT)
    skipped = sum(1 for op in edit_operations[:current_operation_index] if op.status == DiffOp.SKIP)
    
    summary_text = Text(f"Approved: {approved} | Rejected: {rejected} | Skipped: {skipped}", style="loom.accent2")
    
    return Panel(Align.center(summary_text), border_style="dim", padding=(0, 1))

# * Generate dynamic content for each menu option based on current edit operation
def get_diffs_by_opt():
    # If text input is active, show the input interface
    if text_input_active and text_input_mode:
        return {opt: create_text_input_display(text_input_mode) for opt in options}
    
    # Otherwise show normal operation display
    return {
        "Approve": create_operation_display(current_edit_operation),
        "Reject": create_operation_display(current_edit_operation), 
        "Skip": create_operation_display(current_edit_operation),
        "Modify": create_operation_display(current_edit_operation),
        "Prompt": create_operation_display(current_edit_operation),
        "Exit": create_operation_display(current_edit_operation),
    }

# * Render main screen layout w/ header, menu & diff display panels, and footer
def render_screen() -> RenderableType:
    # create main layout w/ 3 rows
    main_layout = Layout()
    main_layout.split_column(
        Layout(name="header", size=3),
        Layout(name="content", ratio=1), 
        Layout(name="footer", size=3)
    )
    
    # create content area w/ menu & diff display
    content_layout = Layout()
    content_layout.split_row(Layout(name="menu", ratio=1), Layout(name="body", ratio=3))

    # create left menu w/ selection highlighting
    row_gap = 1

    grid = Table.grid(padding=0)
    grid.add_column(no_wrap=True)

    for i, opt in enumerate(options):
        is_sel = i == selected
        prefix = "➤ " if is_sel else "  "
        style  = "reverse bold loom.accent" if is_sel else "loom.accent2"
        cell = Text(prefix + opt, style=style)
        bottom = row_gap if i < len(options) - 1 else 0
        grid.add_row(Padding(cell, (0, 0, bottom, 0)))

    menu_panel = Panel(
        Align.center(grid, vertical="top"),
        title="Options",
        border_style="loom.accent2",
        padding=(1, 2),
    )

    # create right diff pane w/ operation details
    current = options[selected]
    diffs_by_opt = get_diffs_by_opt()
    body_panel = Panel(Text("\n").join(diffs_by_opt[current]), title="Current Edit", border_style="loom.accent2")

    content_layout["menu"].update(menu_panel)
    content_layout["body"].update(body_panel)
    
    # update all layout sections
    main_layout["header"].update(create_header_layout())
    main_layout["content"].update(content_layout)
    main_layout["footer"].update(create_footer_layout())

    outer = Panel(main_layout, border_style="loom.accent", width=FIXED_W, height=FIXED_H)
    return Align.left(outer, vertical="top")

# * Main interactive loop for diff review w/ keyboard navigation
def main_display_loop(operations: list[EditOperation] | None = None, filename: str = "document.txt"):
    global selected, current_edit_operation, edit_operations, current_operation_index, current_filename
    global text_input_active, text_input_mode, text_input_buffer, text_input_cursor
    
    # initialize operations & set current state
    if operations:
        edit_operations = operations
        current_operation_index = 0
        current_edit_operation = edit_operations[0] if edit_operations else None
        current_filename = filename
    with Live(render_screen(), console=console, screen=True, refresh_per_second=30) as live:
        VALID_KEYS = {key.UP, key.DOWN, "k", "j", key.ENTER, key.ESC, key.CTRL_C}
        while True:
            k = readkey()

            # handle text input mode
            if text_input_active:
                if k == key.ESC:
                    # cancel text input
                    text_input_active = False
                    text_input_mode = None
                    text_input_buffer = ""
                    text_input_cursor = 0
                    live.update(render_screen())
                    continue
                elif k == key.ENTER:
                    # submit text input
                    if text_input_mode == "modify" and current_edit_operation:
                        # store modified text for processing
                        current_edit_operation.modified_content = text_input_buffer
                        console.print(f"[green]Modified content saved: {text_input_buffer[:50]}...[/]")
                    elif text_input_mode == "prompt" and current_edit_operation:
                        # store prompt instruction for processing
                        current_edit_operation.prompt_instruction = text_input_buffer
                        console.print(f"[cyan]Prompt saved: {text_input_buffer[:50]}...[/]")
                    
                    # reset text input state
                    text_input_active = False
                    text_input_mode = None
                    text_input_buffer = ""
                    text_input_cursor = 0
                    live.update(render_screen())
                    continue
                elif k == key.BACKSPACE:
                    if text_input_cursor > 0:
                        text_input_buffer = text_input_buffer[:text_input_cursor-1] + text_input_buffer[text_input_cursor:]
                        text_input_cursor -= 1
                        live.update(render_screen())
                    continue
                elif k == key.LEFT:
                    if text_input_cursor > 0:
                        text_input_cursor -= 1
                        live.update(render_screen())
                    continue
                elif k == key.RIGHT:
                    if text_input_cursor < len(text_input_buffer):
                        text_input_cursor += 1
                        live.update(render_screen())
                    continue
                elif len(k) == 1 and k.isprintable():
                    # add character at cursor position
                    text_input_buffer = text_input_buffer[:text_input_cursor] + k + text_input_buffer[text_input_cursor:]
                    text_input_cursor += 1
                    live.update(render_screen())
                    continue
                else:
                    continue  # ignore other keys in text input mode

            # filter invalid keystrokes
            if k not in VALID_KEYS:
                continue

            if k in (key.UP, "k"):
                selected = (selected - 1) % len(options)
                live.update(render_screen())
            elif k in (key.DOWN, "j"):
                selected = (selected + 1) % len(options)
                live.update(render_screen())
            elif k == key.ENTER:
                # process user selection & update status
                selected_option = options[selected]
                if selected_option == "Exit":
                    break
                elif current_edit_operation and selected_option in ["Approve", "Reject", "Skip", "Modify", "Prompt"]:
                    # apply user decision to operation
                    if selected_option == "Approve":
                        current_edit_operation.status = DiffOp.APPROVE
                    elif selected_option == "Reject":
                        current_edit_operation.status = DiffOp.REJECT
                    elif selected_option == "Skip":
                        current_edit_operation.status = DiffOp.SKIP
                    elif selected_option == "Modify":
                        current_edit_operation.status = DiffOp.MODIFY
                        # enter text input mode for modification
                        text_input_active = True
                        text_input_mode = "modify"
                        # pre-fill w/ current content
                        text_input_buffer = current_edit_operation.content
                        text_input_cursor = len(text_input_buffer)
                        live.update(render_screen())
                    elif selected_option == "Prompt":
                        current_edit_operation.status = DiffOp.PROMPT
                        # enter text input mode for prompt
                        text_input_active = True
                        text_input_mode = "prompt"
                        # start w/ empty prompt
                        text_input_buffer = ""
                        text_input_cursor = 0
                        live.update(render_screen())
                    
                    # advance to next operation or exit when done
                    current_operation_index += 1
                    if current_operation_index < len(edit_operations):
                        current_edit_operation = edit_operations[current_operation_index]
                        live.update(render_screen())
                    else:
                        break  # all operations complete
                else:
                    break
            elif k in (key.ESC, key.CTRL_C):
                raise SystemExit

    # return operations w/ user decisions applied
    return edit_operations


# execute main loop when run directly
if __name__ == "__main__":
    main_display_loop()
