# src/ui/diff_resolution/diff_display.py
# Interactive diff display interface w/ rich UI components for edit operation review

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
from ...core.pipeline import process_prompt_operation
from ...core.exceptions import AIError, EditError
from ...core.debug import is_debug_enabled, debug_print

options = [
    DiffOp.APPROVE.value.capitalize(),
    DiffOp.REJECT.value.capitalize(),
    DiffOp.SKIP.value.capitalize(),
    DiffOp.MODIFY.value.capitalize(),
    DiffOp.PROMPT.value.capitalize(),
    "Exit",
]
selected = 0

MIN_W, MAX_W = 60, 120
MIN_H, MAX_H = 25, 25


# * Clamp value between min & max bounds
def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


# compute dimensions once
FIXED_W = clamp(console.size.width // 2, MIN_W, MAX_W)
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

# prompt processing state management
prompt_processing = False
prompt_error = None
prompt_processing_contexts = None  # store contexts needed for AI processing

# track if operations were modified during interactive review
operations_modified_during_review = False


# * Convert EditOperation to display format w/ styled text elements
def create_operation_display(edit_op: EditOperation | None) -> list[Text]:
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


# * Create text input display for MODIFY or PROMPT modes
def create_text_input_display(mode: str) -> list[Text]:
    lines: list[Text] = []

    # header
    if mode == "modify":
        lines.append(Text("MODIFY OPERATION", style="bold yellow"))
        lines.append(Text("Edit the suggested content below:", style="dim"))
    elif mode == "prompt":
        lines.append(Text("PROMPT LLM", style="bold cyan"))
        lines.append(Text("Enter additional instructions for the LLM:", style="dim"))

    lines.append(Text(""))

    # current op context (unchanged)
    if current_edit_operation:
        lines.append(Text("Current content:", style="bold"))
        preview = (
            current_edit_operation.content[:100] + "…"
            if len(current_edit_operation.content) > 100
            else current_edit_operation.content
        )
        lines.append(Text(preview, style="dim"))
        lines.append(Text(""))

    # prompt label
    lines.append(Text("Your input:", style="bold"))

    # terminal-like single line input (no panel/box)
    cursor_char = "│" if text_input_cursor == len(text_input_buffer) else "▌"
    display_text = (
        text_input_buffer[:text_input_cursor]
        + cursor_char
        + text_input_buffer[text_input_cursor:]
    )

    # best-effort trimming to visible frame width
    frame_w = max(20, FIXED_W - 6)
    if len(display_text) > frame_w - 2:
        display_text = "…" + display_text[-(frame_w - 3) :]

    lines.append(Text("> " + display_text))

    lines.append(Text(""))
    lines.append(Text("Press [Enter] to submit, [Esc] to cancel", style="dim italic"))
    return lines


# * Create loading display for prompt processing
def create_prompt_loading_display() -> RenderableType:
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
    if current_edit_operation:
        lines.append(Text("Processing operation:", style="bold"))
        lines.append(
            Text(
                f"  {current_edit_operation.operation} at line {current_edit_operation.line_number}",
                style="loom.accent2",
            )
        )
        if current_edit_operation.prompt_instruction:
            instruction_preview = (
                current_edit_operation.prompt_instruction[:80] + "…"
                if len(current_edit_operation.prompt_instruction) > 80
                else current_edit_operation.prompt_instruction
            )
            lines.append(Text(f"  Instruction: {instruction_preview}", style="dim"))
        lines.append(Text(""))

    # loading indicator w/ animated spinner
    if not prompt_error:
        spinner_line = Columns(
            [
                Spinner("dots", style="cyan"),
                Text(" Processing... This may take several seconds.", style="cyan"),
            ]
        )
        lines.append(Text(""))  # spacing
        lines.append(spinner_line)
    else:
        lines.append(Text("⠋ Processing...", style="cyan"))

    lines.append(Text(""))
    lines.append(
        Text("Please wait while the AI generates a new suggestion.", style="dim italic")
    )
    lines.append(Text("Press [Esc] to cancel if needed.", style="dim italic"))

    # error display if present
    if prompt_error:
        lines.append(Text(""))
        lines.append(Text("Error occurred:", style="bold red"))
        lines.append(Text(str(prompt_error), style="red"))
        lines.append(Text(""))
        lines.append(
            Text("Press [Enter] to continue with original edit", style="dim italic")
        )

    # return as group for proper rendering
    from rich.console import Group

    return Group(*lines)


# * Create header layout w/ filename & progress info
def create_header_layout() -> RenderableType:
    total_ops = len(edit_operations)
    current_num = min(current_operation_index + 1, total_ops)

    left_text = Text(f"Reviewing: {current_filename}", style="bold loom.accent")
    right_text = Text(f"Suggestion {current_num} of {total_ops}", style="loom.accent2")

    # expand=True lets grid fill panel; left column takes remaining space
    header_table = Table.grid(padding=0, expand=True)
    header_table.add_column(ratio=1, justify="left")
    header_table.add_column(no_wrap=True, justify="right")
    header_table.add_row(left_text, right_text)

    return Panel(header_table, border_style="dim", padding=(0, 1))


# * Create footer layout w/ approval/rejection/skip counts
def create_footer_layout() -> RenderableType:
    approved = sum(
        1
        for op in edit_operations[:current_operation_index]
        if op.status == DiffOp.APPROVE
    )
    rejected = sum(
        1
        for op in edit_operations[:current_operation_index]
        if op.status == DiffOp.REJECT
    )
    skipped = sum(
        1
        for op in edit_operations[:current_operation_index]
        if op.status == DiffOp.SKIP
    )

    summary_text = Text(
        f"Approved: {approved} | Rejected: {rejected} | Skipped: {skipped}",
        style="loom.accent2",
    )

    return Panel(Align.center(summary_text), border_style="dim", padding=(0, 1))


# * Generate dynamic content for each menu option based on current edit operation
def get_diffs_by_opt() -> dict:
    # If prompt is being processed, show loading interface
    if prompt_processing:
        loading_display = create_prompt_loading_display()
        return {opt: loading_display for opt in options}

    # If text input is active, show the input interface
    if text_input_active and text_input_mode:
        input_lines = create_text_input_display(text_input_mode)
        return {opt: input_lines for opt in options}

    # Otherwise show normal operation display
    op_lines = create_operation_display(current_edit_operation)
    return {
        "Approve": op_lines,
        "Reject": op_lines,
        "Skip": op_lines,
        "Modify": op_lines,
        "Prompt": op_lines,
        "Exit": op_lines,
    }


# * Render main screen layout w/ header, menu & diff display panels, & footer
def render_screen() -> RenderableType:
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

    for i, opt in enumerate(options):
        is_sel = i == selected
        prefix = "➤ " if is_sel else "  "
        style = "reverse bold loom.accent" if is_sel else "loom.accent2"
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
    body_content_list = diffs_by_opt[current]
    # join list of Text objects for display
    if isinstance(body_content_list, list):
        body_content = Text("\n").join(body_content_list)
    else:
        body_content = body_content_list
    body_panel = Panel(body_content, title="Current Edit", border_style="loom.accent2")

    content_layout["menu"].update(menu_panel)
    content_layout["body"].update(body_panel)

    # update all layout sections
    main_layout["header"].update(create_header_layout())
    main_layout["content"].update(content_layout)
    main_layout["footer"].update(create_footer_layout())

    outer = Panel(
        main_layout, border_style="loom.accent", width=FIXED_W, height=FIXED_H
    )
    return Align.left(outer, vertical="top")


# * Process prompt instruction immediately using AI & update operation content
def process_prompt_immediately(
    operation: EditOperation,
    resume_lines: Lines,
    job_text: str,
    sections_json: str | None,
    model: str,
) -> bool:
    global prompt_error
    prompt_error = None

    try:
        prompt_preview = operation.prompt_instruction or "(empty)"
        if is_debug_enabled():
            debug_print(
                f"Processing prompt: '{prompt_preview[:50]}{'...' if len(prompt_preview) > 50 else ''}'",
                "DIFF",
            )

        # call the core prompt processing function
        updated_operation = process_prompt_operation(
            operation, resume_lines, job_text, sections_json, model
        )

        # update the current operation w/ new content
        operation.content = updated_operation.content
        operation.reasoning = updated_operation.reasoning
        operation.confidence = updated_operation.confidence

        # clear prompt instruction since it's been processed
        operation.prompt_instruction = None
        # status remains unchanged so user can decide on new content

        if is_debug_enabled():
            debug_print(
                f"AI generated {len(operation.content)} characters of new content",
                "DIFF",
            )
        return True

    except (AIError, EditError) as e:
        prompt_error = str(e)
        console.print(f"[red]AI Error: {e}[/]")
        return False
    except Exception as e:
        prompt_error = f"Unexpected error: {str(e)}"
        console.print(f"[red]Unexpected Error: {e}[/]")
        return False


# * Main interactive loop for diff review w/ keyboard navigation
def main_display_loop(
    operations: list[EditOperation] | None = None,
    filename: str = "document.txt",
    resume_lines: Lines | None = None,
    job_text: str | None = None,
    sections_json: str | None = None,
    model: str | None = None,
) -> tuple[list[EditOperation], bool]:
    global selected, current_edit_operation, edit_operations, current_operation_index, current_filename
    global text_input_active, text_input_mode, text_input_buffer, text_input_cursor
    global prompt_processing, prompt_error, prompt_processing_contexts, operations_modified_during_review

    # initialize operations & set current state
    global operations_modified_during_review
    operations_modified_during_review = False  # reset the flag

    if operations:
        edit_operations = operations
        current_operation_index = 0
        current_edit_operation = edit_operations[0] if edit_operations else None
        current_filename = filename

    # store AI processing contexts for prompt operations
    prompt_processing_contexts = {
        "resume_lines": resume_lines,
        "job_text": job_text,
        "sections_json": sections_json,
        "model": model,
    }
    with Live(
        render_screen(), console=console, screen=True, refresh_per_second=30
    ) as live:
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
                        # immediately update operation content w/ modified text
                        current_edit_operation.content = text_input_buffer
                        # track that operations were modified
                        operations_modified_during_review = True
                        if is_debug_enabled():
                            debug_print(
                                f"Content modified: {text_input_buffer[:50]}...", "DIFF"
                            )
                    elif text_input_mode == "prompt" and current_edit_operation:
                        # store prompt instruction & trigger immediate AI processing
                        current_edit_operation.prompt_instruction = text_input_buffer

                        # switch to prompt processing mode
                        prompt_processing = True
                        prompt_error = None

                        # reset text input state first
                        text_input_active = False
                        text_input_mode = None
                        text_input_buffer = ""
                        text_input_cursor = 0

                        # CRITICAL: Force refresh loading screen before blocking call
                        live.update(render_screen())
                        live.refresh()  # Force immediate render

                        # Import time for timing & delays
                        import time

                        # Track loading start time for minimum duration
                        loading_start_time = time.time()
                        if is_debug_enabled():
                            debug_print(
                                f"Starting AI processing at {time.strftime('%H:%M:%S')}...",
                                "DIFF",
                            )

                        # Small delay to ensure the loading screen actually displays
                        time.sleep(0.1)  # 100ms to let the loading screen appear

                        # check required contexts for AI processing
                        if (
                            prompt_processing_contexts
                            and prompt_processing_contexts["resume_lines"] is not None
                            and prompt_processing_contexts["job_text"] is not None
                            and prompt_processing_contexts["model"] is not None
                        ):

                            # process the prompt immediately (blocking call)
                            ai_start_time = time.time()
                            if is_debug_enabled():
                                debug_print(
                                    f"Calling AI model '{prompt_processing_contexts['model']}'...",
                                    "DIFF",
                                )

                            success = process_prompt_immediately(
                                current_edit_operation,
                                prompt_processing_contexts["resume_lines"],
                                prompt_processing_contexts["job_text"],
                                prompt_processing_contexts["sections_json"],
                                prompt_processing_contexts["model"],
                            )

                            ai_duration = time.time() - ai_start_time
                            if is_debug_enabled():
                                debug_print(
                                    f"AI call completed in {ai_duration:.2f} seconds",
                                    "DIFF",
                                )

                            # ensure minimum loading screen duration (1.5 seconds total)
                            total_elapsed = time.time() - loading_start_time
                            min_duration = 1.5
                            if total_elapsed < min_duration:
                                remaining_time = min_duration - total_elapsed
                                if is_debug_enabled():
                                    debug_print(
                                        f"Ensuring minimum loading duration... {remaining_time:.1f}s remaining",
                                        "DIFF",
                                    )
                                time.sleep(remaining_time)

                            # processing complete - exit loading state
                            prompt_processing = False
                            live.update(render_screen())

                            if success:
                                # track that operations were modified
                                operations_modified_during_review = True
                                console.print(
                                    "[green]AI regenerated the edit based on your prompt[/]"
                                )
                            else:
                                console.print(
                                    f"[red]Error processing prompt: {prompt_error}[/]"
                                )
                                # keep loading screen visible w/ error for user to acknowledge
                                prompt_processing = (
                                    True  # keep in processing mode to show error
                                )
                                live.update(render_screen())
                        else:
                            # missing required contexts for AI processing
                            console.print(
                                "[red]Missing required context for AI processing![/]"
                            )
                            prompt_error = "Missing required context for AI processing (resume, job, or model)"
                            # ensure minimum display time even for errors
                            total_elapsed = time.time() - loading_start_time
                            min_duration = 1.5
                            if total_elapsed < min_duration:
                                remaining_time = min_duration - total_elapsed
                                time.sleep(remaining_time)
                            prompt_processing = (
                                True  # keep in processing mode to show error
                            )
                            live.update(render_screen())

                        continue

                    # reset text input state
                    text_input_active = False
                    text_input_mode = None
                    text_input_buffer = ""
                    text_input_cursor = 0
                    live.update(render_screen())
                    continue
                elif k == key.BACKSPACE:
                    if text_input_cursor > 0:
                        text_input_buffer = (
                            text_input_buffer[: text_input_cursor - 1]
                            + text_input_buffer[text_input_cursor:]
                        )
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
                    text_input_buffer = (
                        text_input_buffer[:text_input_cursor]
                        + k
                        + text_input_buffer[text_input_cursor:]
                    )
                    text_input_cursor += 1
                    live.update(render_screen())
                    continue
                else:
                    continue  # ignore other keys in text input mode

            # handle prompt processing mode
            if prompt_processing:
                if k == key.ENTER and prompt_error:
                    # user acknowledged error, continue w/ original edit
                    prompt_processing = False
                    prompt_error = None
                    live.update(render_screen())
                elif k in (key.ESC, key.CTRL_C):
                    # cancel prompt processing
                    prompt_processing = False
                    prompt_error = None
                    live.update(render_screen())
                continue  # ignore other keys during processing

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
                elif current_edit_operation and selected_option in [
                    "Approve",
                    "Reject",
                    "Skip",
                    "Modify",
                    "Prompt",
                ]:
                    # apply user decision to operation
                    if selected_option == "Approve":
                        current_edit_operation.status = DiffOp.APPROVE
                    elif selected_option == "Reject":
                        current_edit_operation.status = DiffOp.REJECT
                    elif selected_option == "Skip":
                        current_edit_operation.status = DiffOp.SKIP
                    elif selected_option == "Modify":
                        # enter text input mode for modification (don't set status yet)
                        text_input_active = True
                        text_input_mode = "modify"
                        # pre-fill w/ current content
                        text_input_buffer = current_edit_operation.content
                        text_input_cursor = len(text_input_buffer)
                        live.update(render_screen())
                        continue  # don't advance to next operation yet
                    elif selected_option == "Prompt":
                        # enter text input mode for prompt (don't set status yet)
                        text_input_active = True
                        text_input_mode = "prompt"
                        # start w/ empty prompt
                        text_input_buffer = ""
                        text_input_cursor = 0
                        live.update(render_screen())
                        continue  # don't advance to next operation yet

                    # advance to next operation or exit when done
                    current_operation_index += 1
                    if current_operation_index < len(edit_operations):
                        current_edit_operation = edit_operations[
                            current_operation_index
                        ]
                        live.update(render_screen())
                    else:
                        break  # all operations complete
                else:
                    break
            elif k in (key.ESC, key.CTRL_C):
                raise SystemExit

    # return operations w/ user decisions & modification flag
    return edit_operations, operations_modified_during_review


# execute main loop when run directly
if __name__ == "__main__":
    main_display_loop()
