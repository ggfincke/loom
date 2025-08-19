# src/ui/diff_resolution/diff_display.py
# Interactive diff display interface w/ rich UI components for edit operation review

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

options = [DiffOp.APPROVE.value.capitalize(), DiffOp.REJECT.value.capitalize(), DiffOp.SKIP.value.capitalize(), "Exit"]
selected = 0

MIN_W, MAX_W = 60, 120
MIN_H, MAX_H = 25, 25

# clamp value between min & max bounds
def clamp(n, lo, hi): 
    return max(lo, min(hi, n))

# compute once
FIXED_W = clamp(console.size.width  // 2, MIN_W, MAX_W)
FIXED_H = clamp(console.size.height // 2, MIN_H, MAX_H)

# global variables for current edit operation data
current_edit_operation = None
edit_operations = []
current_operation_index = 0
current_filename = "document.txt"

# * Convert EditOperation to display format w/ styled text elements
def create_operation_display(edit_op: EditOperation | None) -> list[Text]:
    if edit_op is None:
        return [Text("No edit operation selected", style="dim")]
    
    lines = []
    
    # operation header
    lines.append(Text(f"Operation: {edit_op.operation}", style="bold loom.accent"))
    lines.append(Text(f"Line: {edit_op.line_number}", style="loom.accent2"))
    if edit_op.confidence > 0:
        lines.append(Text(f"Confidence: {edit_op.confidence:.2f}", style="loom.accent2"))
    lines.append(Text(""))
    
    # operation-specific display
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
    
    # reasoning
    if edit_op.reasoning:
        lines.append(Text(""))
        lines.append(Text("Reasoning:", style="bold"))
        lines.append(Text(edit_op.reasoning, style="dim"))
    
    return lines

# * Create header layout w/ filename & progress info
def create_header_layout() -> RenderableType:
    total_ops = len(edit_operations)
    current_num = min(current_operation_index + 1, total_ops)

    left_text  = Text(f"Reviewing: {current_filename}", style="bold loom.accent")
    right_text = Text(f"Suggestion {current_num} of {total_ops}", style="loom.accent2")

    # expand=True lets the grid fill the panel; left column eats the slack space
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

# generate dynamic content for each menu option based on current edit operation
def get_diffs_by_opt():
    return {
        "Approve": create_operation_display(current_edit_operation),
        "Reject": create_operation_display(current_edit_operation), 
        "Skip": create_operation_display(current_edit_operation),
        "Exit": create_operation_display(current_edit_operation),
    }

# * Render main screen layout w/ header, menu & diff display panels, and footer
def render_screen() -> RenderableType:
    # create main 3-row layout
    main_layout = Layout()
    main_layout.split_column(
        Layout(name="header", size=3),
        Layout(name="content", ratio=1), 
        Layout(name="footer", size=3)
    )
    
    # create content area w/ menu & body
    content_layout = Layout()
    content_layout.split_row(Layout(name="menu", ratio=1), Layout(name="body", ratio=3))

    # create left menu w/ highlighted selection
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

    # create right diff pane showing operation details
    current = options[selected]
    diffs_by_opt = get_diffs_by_opt()
    body_panel = Panel(Text("\n").join(diffs_by_opt[current]), title="Current Edit", border_style="loom.accent2")

    content_layout["menu"].update(menu_panel)
    content_layout["body"].update(body_panel)
    
    # update main layout sections
    main_layout["header"].update(create_header_layout())
    main_layout["content"].update(content_layout)
    main_layout["footer"].update(create_footer_layout())

    outer = Panel(main_layout, border_style="loom.accent", width=FIXED_W, height=FIXED_H)
    return Align.left(outer, vertical="top")

# * Main interactive loop for diff review w/ keyboard navigation
def main_display_loop(operations: list[EditOperation] | None = None, filename: str = "document.txt"):
    global selected, current_edit_operation, edit_operations, current_operation_index, current_filename
    
    # initialize edit operations & set current operation
    if operations:
        edit_operations = operations
        current_operation_index = 0
        current_edit_operation = edit_operations[0] if edit_operations else None
        current_filename = filename
    with Live(render_screen(), console=console, screen=True, refresh_per_second=30) as live:
        VALID_KEYS = {key.UP, key.DOWN, "k", "j", key.ENTER, key.ESC, key.CTRL_C}
        while True:
            k = readkey()

            # filter out invalid keystrokes
            if k not in VALID_KEYS:
                continue

            if k in (key.UP, "k"):
                selected = (selected - 1) % len(options)
                live.update(render_screen())
            elif k in (key.DOWN, "j"):
                selected = (selected + 1) % len(options)
                live.update(render_screen())
            elif k == key.ENTER:
                # process user selection & update operation status
                selected_option = options[selected]
                if selected_option == "Exit":
                    break
                elif current_edit_operation and selected_option in ["Approve", "Reject", "Skip"]:
                    # apply user decision to current operation
                    if selected_option == "Approve":
                        current_edit_operation.status = DiffOp.APPROVE
                    elif selected_option == "Reject":
                        current_edit_operation.status = DiffOp.REJECT
                    elif selected_option == "Skip":
                        current_edit_operation.status = DiffOp.SKIP
                    
                    # advance to next operation or exit if done
                    current_operation_index += 1
                    if current_operation_index < len(edit_operations):
                        current_edit_operation = edit_operations[current_operation_index]
                        live.update(render_screen())
                    else:
                        break  # all operations processed
                else:
                    break
            elif k in (key.ESC, key.CTRL_C):
                raise SystemExit

    # return edit operations w/ user decisions applied
    return edit_operations


# execute main loop when run directly
if __name__ == "__main__":
    main_display_loop()
