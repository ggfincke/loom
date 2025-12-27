# tests/unit/ui/diff_resolution/test_diff_display.py
# Unit tests for diff display UI components & interactive functionality

from unittest.mock import Mock, patch, MagicMock

from src.ui.core.rich_components import Text
from src.ui.diff_resolution.diff_display import (
    _clamp,
    InteractiveDiffResolver,
    DiffReviewMode,
    main_display_loop,
    OPTIONS,
)
from src.core.constants import EditOperation, DiffOp


# * Test clamp utility function for boundary value handling


class TestClampFunction:
    # * Verify clamp within bounds
    def test_clamp_within_bounds(self):
        assert _clamp(5, 1, 10) == 5
        assert _clamp(7, 3, 15) == 7

    # * Verify clamp at lower bound
    def test_clamp_at_lower_bound(self):
        assert _clamp(-5, 0, 10) == 0
        assert _clamp(2, 5, 15) == 5

    # * Verify clamp at upper bound
    def test_clamp_at_upper_bound(self):
        assert _clamp(20, 0, 10) == 10
        assert _clamp(100, 5, 50) == 50

    # * Verify clamp equal bounds
    def test_clamp_equal_bounds(self):
        assert _clamp(5, 10, 10) == 10
        assert _clamp(15, 10, 10) == 10

    # * Verify clamp negative numbers
    def test_clamp_negative_numbers(self):
        assert _clamp(-15, -10, -5) == -10
        assert _clamp(-3, -10, -5) == -5
        assert _clamp(-7, -10, -5) == -7


# * Test InteractiveDiffResolver initialization


class TestInteractiveDiffResolverInit:
    # * Verify init w/ operations
    def test_init_with_operations(self):
        ops = [
            EditOperation(operation="replace_line", line_number=1, content="test1"),
            EditOperation(operation="replace_line", line_number=2, content="test2"),
        ]
        resolver = InteractiveDiffResolver(ops, filename="test.docx")

        assert resolver.operations == ops
        assert resolver.state.filename == "test.docx"
        assert resolver.state.current_index == 0
        assert resolver.state.selected == 0
        assert resolver.state.mode == DiffReviewMode.MENU
        assert resolver.state.operations_modified is False

    # * Verify init w/ ai context
    def test_init_with_ai_context(self):
        ops = [EditOperation(operation="replace_line", line_number=1, content="test")]
        resolver = InteractiveDiffResolver(
            ops,
            resume_lines={1: "line1"},
            job_text="job desc",
            sections_json='{"sections": []}',
            model="gpt-4o",
        )

        assert resolver.ai_processor.context.resume_lines == {1: "line1"}
        assert resolver.ai_processor.context.job_text == "job desc"
        assert resolver.ai_processor.context.model == "gpt-4o"

    # * Verify current operation property
    def test_current_operation_property(self):
        ops = [
            EditOperation(operation="replace_line", line_number=1, content="test1"),
            EditOperation(operation="replace_line", line_number=2, content="test2"),
        ]
        resolver = InteractiveDiffResolver(ops)

        assert resolver.state.current_operation == ops[0]
        resolver.state.current_index = 1
        assert resolver.state.current_operation == ops[1]
        resolver.state.current_index = 10  # out of bounds
        assert resolver.state.current_operation is None

    # * Verify is complete property
    def test_is_complete_property(self):
        ops = [EditOperation(operation="replace_line", line_number=1, content="test")]
        resolver = InteractiveDiffResolver(ops)

        assert resolver.is_complete is False
        resolver.state.current_index = 1
        assert resolver.is_complete is True


# * Test operation display formatting


class TestRenderOperationDisplay:
    # * Verify none operation
    def test_none_operation(self):
        resolver = InteractiveDiffResolver([])
        result = resolver.renderer.render_operation_display(
            resolver.state.current_operation
        )
        assert len(result) == 1
        assert "No edit operation selected" in str(result[0])

    # * Verify replace line operation
    def test_replace_line_operation(self):
        op = EditOperation(
            operation="replace_line",
            line_number=5,
            content="New content",
            original_content="Old content",
            reasoning="Test reasoning",
            confidence=0.85,
        )
        resolver = InteractiveDiffResolver([op])

        result = resolver.renderer.render_operation_display(
            resolver.state.current_operation
        )
        content_lines = [str(line) for line in result]

        assert any("replace_line" in line for line in content_lines)
        assert any("Line: 5" in line for line in content_lines)
        assert any("Confidence: 0.85" in line for line in content_lines)
        assert any("Old content" in line for line in content_lines)
        assert any("New content" in line for line in content_lines)
        assert any("Test reasoning" in line for line in content_lines)

    # * Verify replace range operation
    def test_replace_range_operation(self):
        op = EditOperation(
            operation="replace_range",
            line_number=10,
            start_line=10,
            end_line=12,
            content="Range replacement",
            original_content="Original range content",
            confidence=0.92,
        )
        resolver = InteractiveDiffResolver([op])

        result = resolver.renderer.render_operation_display(
            resolver.state.current_operation
        )
        content_lines = [str(line) for line in result]

        assert any("replace_range" in line for line in content_lines)
        assert any("Lines 10-12" in line for line in content_lines)

    # * Verify insert after operation
    def test_insert_after_operation(self):
        op = EditOperation(
            operation="insert_after",
            line_number=8,
            content="Inserted content",
            reasoning="Adding new information",
        )
        resolver = InteractiveDiffResolver([op])

        result = resolver.renderer.render_operation_display(
            resolver.state.current_operation
        )
        content_lines = [str(line) for line in result]

        assert any("insert_after" in line for line in content_lines)
        assert any("Insert after line 8" in line for line in content_lines)

    # * Verify delete range operation
    def test_delete_range_operation(self):
        op = EditOperation(
            operation="delete_range",
            line_number=15,
            start_line=15,
            end_line=17,
            reasoning="Removing outdated content",
        )
        resolver = InteractiveDiffResolver([op])

        result = resolver.renderer.render_operation_display(
            resolver.state.current_operation
        )
        content_lines = [str(line) for line in result]

        assert any("delete_range" in line for line in content_lines)
        assert any("Delete lines 15-17" in line for line in content_lines)

    # * Verify operation without confidence
    def test_operation_without_confidence(self):
        op = EditOperation(
            operation="replace_line", line_number=3, content="Test content"
        )
        resolver = InteractiveDiffResolver([op])

        result = resolver.renderer.render_operation_display(
            resolver.state.current_operation
        )
        content_lines = [str(line) for line in result]

        assert not any("Confidence: 0.00" in line for line in content_lines)

    # * Verify operation w/ no original content
    def test_operation_with_no_original_content(self):
        op = EditOperation(
            operation="replace_line", line_number=5, content="New content"
        )
        resolver = InteractiveDiffResolver([op])

        result = resolver.renderer.render_operation_display(
            resolver.state.current_operation
        )
        content_lines = [str(line) for line in result]

        assert any("[no content]" in line for line in content_lines)


# * Test text input display


class TestRenderTextInputDisplay:
    # * Verify modify mode display
    def test_modify_mode_display(self):
        op = EditOperation(
            operation="replace_line", line_number=5, content="Original content"
        )
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.TEXT_INPUT
        resolver.state.text_input_mode = "modify"
        resolver.state.text_input_buffer = "test input"
        resolver.state.text_input_cursor = 5

        result = resolver.renderer.render_text_input_display(resolver.state)
        content_lines = [str(line) for line in result]

        assert any("MODIFY OPERATION" in line for line in content_lines)
        assert any("Edit the suggested content below" in line for line in content_lines)

    # * Verify prompt mode display
    def test_prompt_mode_display(self):
        op = EditOperation(
            operation="replace_line", line_number=5, content="Original content"
        )
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.TEXT_INPUT
        resolver.state.text_input_mode = "prompt"

        result = resolver.renderer.render_text_input_display(resolver.state)
        content_lines = [str(line) for line in result]

        assert any("PROMPT LLM" in line for line in content_lines)
        assert any("Enter additional instructions" in line for line in content_lines)


# * Test header & footer layout


class TestHeaderFooterLayouts:
    # * Verify header w/ operations
    def test_header_with_operations(self):
        ops = [
            EditOperation(operation="replace_line", line_number=1, content="test1"),
            EditOperation(operation="replace_line", line_number=2, content="test2"),
        ]
        resolver = InteractiveDiffResolver(ops, filename="resume.docx")

        result = resolver.renderer.render_header(
            resolver.state.filename,
            resolver.state.current_index,
            len(resolver.state.operations),
        )
        assert result is not None

    # * Verify footer w/ processed operations
    def test_footer_with_processed_operations(self):
        op1 = EditOperation(operation="replace_line", line_number=1, content="t1")
        op2 = EditOperation(operation="replace_line", line_number=2, content="t2")
        op3 = EditOperation(operation="replace_line", line_number=3, content="t3")

        op1.status = DiffOp.APPROVE
        op2.status = DiffOp.REJECT
        op3.status = DiffOp.SKIP

        resolver = InteractiveDiffResolver([op1, op2, op3])
        resolver.state.current_index = 3  # all operations reviewed

        result = resolver.renderer.render_footer(
            resolver.state.operations, resolver.state.current_index
        )
        assert result is not None


# * Test key handling


class TestKeyHandling:
    # * Verify menu navigation up
    def test_menu_navigation_up(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.selected = 1

        from readchar import key

        resolver.input_handler._handle_menu_key(key.UP)
        assert resolver.state.selected == 0

    # * Verify menu navigation down
    def test_menu_navigation_down(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.selected = 0

        from readchar import key

        resolver.input_handler._handle_menu_key(key.DOWN)
        assert resolver.state.selected == 1

    # * Verify text input backspace
    def test_text_input_backspace(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.TEXT_INPUT
        resolver.state.text_input_buffer = "hello"
        resolver.state.text_input_cursor = 5

        from readchar import key

        resolver.input_handler._handle_text_input_key(key.BACKSPACE)
        assert resolver.state.text_input_buffer == "hell"
        assert resolver.state.text_input_cursor == 4

    # * Verify text input typing
    def test_text_input_typing(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.TEXT_INPUT
        resolver.state.text_input_buffer = ""
        resolver.state.text_input_cursor = 0

        resolver.input_handler._handle_text_input_key("a")
        assert resolver.state.text_input_buffer == "a"
        assert resolver.state.text_input_cursor == 1

    # * Verify text input escape cancels
    def test_text_input_escape_cancels(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.TEXT_INPUT
        resolver.state.text_input_mode = "modify"
        resolver.state.text_input_buffer = "some input"

        from readchar import key

        resolver.input_handler._handle_text_input_key(key.ESC)

        assert resolver.state.mode == DiffReviewMode.MENU
        assert resolver.state.text_input_buffer == ""
        assert resolver.state.text_input_mode is None


# * Test operation actions


class TestOperationActions:
    # * Verify approve sets status
    def test_approve_sets_status(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.selected = 0  # Approve

        resolver.input_handler._process_menu_selection()

        assert op.status == DiffOp.APPROVE
        assert resolver.state.current_index == 1

    # * Verify reject sets status
    def test_reject_sets_status(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.selected = 1  # Reject

        resolver.input_handler._process_menu_selection()

        assert op.status == DiffOp.REJECT
        assert resolver.state.current_index == 1

    # * Verify skip sets status
    def test_skip_sets_status(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.selected = 2  # Skip

        resolver.input_handler._process_menu_selection()

        assert op.status == DiffOp.SKIP
        assert resolver.state.current_index == 1

    # * Verify modify enters text input mode
    def test_modify_enters_text_input_mode(self):
        op = EditOperation(operation="replace_line", line_number=1, content="original")
        resolver = InteractiveDiffResolver([op])
        resolver.state.selected = 3  # Modify

        resolver.input_handler._process_menu_selection()

        assert resolver.state.mode == DiffReviewMode.TEXT_INPUT
        assert resolver.state.text_input_mode == "modify"
        assert resolver.state.text_input_buffer == "original"

    # * Verify prompt enters text input mode
    def test_prompt_enters_text_input_mode(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.selected = 4  # Prompt

        resolver.input_handler._process_menu_selection()

        assert resolver.state.mode == DiffReviewMode.TEXT_INPUT
        assert resolver.state.text_input_mode == "prompt"
        assert resolver.state.text_input_buffer == ""

    # * Verify exit returns false
    def test_exit_returns_false(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.selected = 5  # Exit

        result = resolver.input_handler._process_menu_selection()

        assert result is False

    # * Verify submit modify updates content
    def test_submit_modify_updates_content(self):
        op = EditOperation(operation="replace_line", line_number=1, content="original")
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.TEXT_INPUT
        resolver.state.text_input_mode = "modify"
        resolver.state.text_input_buffer = "modified content"

        resolver._state_manager.submit_modify()

        assert op.content == "modified content"
        assert resolver.state.operations_modified is True
        assert resolver.state.mode == DiffReviewMode.MENU

    # * Verify submit prompt transitions to processing
    def test_submit_prompt_transitions_to_processing(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.TEXT_INPUT
        resolver.state.text_input_mode = "prompt"
        resolver.state.text_input_buffer = "make it better"

        resolver._state_manager.submit_prompt()

        assert op.prompt_instruction == "make it better"
        assert resolver.state.mode == DiffReviewMode.PROMPT_PROCESSING
        assert resolver.state.text_input_buffer == ""


# * Test main display loop


class TestMainDisplayLoop:
    @patch("src.ui.diff_resolution.diff_display.Live")
    @patch("src.ui.diff_resolution.diff_display.readkey")
    # * Verify main display loop initialization
    def test_main_display_loop_initialization(self, mock_readkey, mock_live):
        from readchar import key

        mock_readkey.return_value = key.ESC
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__.return_value = mock_live_instance

        test_ops = [
            EditOperation(operation="replace_line", line_number=1, content="test1"),
        ]

        try:
            main_display_loop(test_ops, "test_file.txt")
        except SystemExit:
            pass  # expected from ESC key

        mock_live.assert_called_once()

    @patch("src.ui.diff_resolution.diff_display.Live")
    @patch("src.ui.diff_resolution.diff_display.readkey")
    # * Verify main display loop w/ none operations
    def test_main_display_loop_with_none_operations(self, mock_readkey, mock_live):
        from readchar import key

        mock_readkey.return_value = key.ESC
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__.return_value = mock_live_instance

        # should handle None operations gracefully (becomes empty list)
        try:
            result = main_display_loop(None, "test.txt")
            # w/ no operations, should complete immediately
            assert result == ([], False)
        except SystemExit:
            pass  # might exit depending on state

    @patch("src.ui.diff_resolution.diff_display.Live")
    @patch("src.ui.diff_resolution.diff_display.readkey")
    # * Verify main display loop returns result
    def test_main_display_loop_returns_result(self, mock_readkey, mock_live):
        from readchar import key

        # simulate approving one operation then exiting
        mock_readkey.side_effect = [key.ENTER, key.ESC]  # Approve, then ESC
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__.return_value = mock_live_instance

        test_op = EditOperation(operation="replace_line", line_number=1, content="test")
        test_ops = [test_op]

        try:
            result = main_display_loop(test_ops, "test.txt")
            # should return the operations & modification flag
            ops, modified = result
            assert ops == test_ops
        except SystemExit:
            pass  # ESC causes system exit


# * Test prompt processing w/ callback


class TestPromptProcessingCallback:
    # * Verify callback receives correct args
    def test_callback_receives_correct_args(self):
        callback_received = {}

        def mock_callback(op, lines, job, sections, model):
            callback_received["op"] = op
            callback_received["lines"] = lines
            callback_received["job"] = job
            callback_received["model"] = model
            op.content = "updated content"
            return True

        op = EditOperation(operation="replace_line", line_number=1, content="original")
        op.prompt_instruction = "improve this"

        resolver = InteractiveDiffResolver(
            [op],
            resume_lines={1: "line"},
            job_text="job desc",
            model="gpt-4o",
            on_prompt_regenerate=mock_callback,
        )
        resolver.state.mode = DiffReviewMode.PROMPT_PROCESSING

        # create mock live for process_prompt
        mock_live = MagicMock()

        resolver.ai_processor.process_prompt(mock_live)

        assert callback_received["op"] == op
        assert callback_received["lines"] == {1: "line"}
        assert callback_received["job"] == "job desc"
        assert callback_received["model"] == "gpt-4o"

    # * Verify callback error sets prompt error
    def test_callback_error_sets_prompt_error(self):
        def failing_callback(op, lines, job, sections, model):
            from src.core.exceptions import AIError

            raise AIError("API error")

        op = EditOperation(operation="replace_line", line_number=1, content="original")
        op.prompt_instruction = "improve"

        resolver = InteractiveDiffResolver(
            [op],
            resume_lines={1: "line"},
            job_text="job",
            model="gpt-4o",
            on_prompt_regenerate=failing_callback,
        )
        resolver.state.mode = DiffReviewMode.PROMPT_PROCESSING

        mock_live = MagicMock()
        resolver.ai_processor.process_prompt(mock_live)

        assert resolver.state.prompt_error is not None
        assert "API error" in resolver.state.prompt_error


# * Test get_result


class TestGetResult:
    # * Verify returns operations & modified flag
    def test_returns_operations_and_modified_flag(self):
        ops = [
            EditOperation(operation="replace_line", line_number=1, content="test"),
        ]
        resolver = InteractiveDiffResolver(ops)
        resolver.state.operations_modified = True

        result_ops, modified = resolver.get_result()

        assert result_ops == ops
        assert modified is True


# * Test render_screen integration


class TestRenderScreen:
    # * Verify render screen menu mode
    def test_render_screen_menu_mode(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op], filename="test.txt")

        result = resolver.render_screen()
        assert result is not None

    # * Verify render screen text input mode
    def test_render_screen_text_input_mode(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.TEXT_INPUT
        resolver.state.text_input_mode = "modify"

        result = resolver.render_screen()
        assert result is not None

    # * Verify render screen prompt processing mode
    def test_render_screen_prompt_processing_mode(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.PROMPT_PROCESSING

        result = resolver.render_screen()
        assert result is not None

    # * Verify render screen w/ error
    def test_render_screen_with_error(self):
        op = EditOperation(operation="replace_line", line_number=1, content="test")
        resolver = InteractiveDiffResolver([op])
        resolver.state.mode = DiffReviewMode.PROMPT_PROCESSING
        resolver.state.prompt_error = "Something went wrong"

        result = resolver.render_screen()
        assert result is not None
