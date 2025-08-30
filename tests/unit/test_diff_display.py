# tests/unit/test_diff_display.py
# Unit tests for diff display UI components & interactive functionality

from unittest.mock import Mock, patch, MagicMock
from src.ui.core.rich_components import Text

from src.ui.diff_resolution.diff_display import (
    clamp, create_operation_display, create_header_layout, create_footer_layout,
    get_diffs_by_opt, render_screen
)
from src.core.constants import EditOperation, DiffOp


# * Test clamp utility function for boundary value handling

class TestClampFunction:
    # * Test clamp function w/ values within specified bounds
    def test_clamp_within_bounds(self):
        assert clamp(5, 1, 10) == 5
        assert clamp(7, 3, 15) == 7
    
    # * Test clamp function clamping to lower boundary
    def test_clamp_at_lower_bound(self):
        assert clamp(-5, 0, 10) == 0
        assert clamp(2, 5, 15) == 5
    
    # * Test clamp function clamping to upper boundary
    def test_clamp_at_upper_bound(self):
        assert clamp(20, 0, 10) == 10
        assert clamp(100, 5, 50) == 50
    
    # * Test clamp function w/ equal min & max bounds
    def test_clamp_equal_bounds(self):
        assert clamp(5, 10, 10) == 10
        assert clamp(15, 10, 10) == 10
    
    # * Test clamp function w/ negative number ranges
    def test_clamp_negative_numbers(self):
        assert clamp(-15, -10, -5) == -10
        assert clamp(-3, -10, -5) == -5
        assert clamp(-7, -10, -5) == -7


# * Test operation display formatting for different EditOperation types

class TestCreateOperationDisplay:
    # * Test display formatting when EditOperation is None
    def test_none_operation(self):
        result = create_operation_display(None)
        assert len(result) == 1
        assert isinstance(result[0], Text)
        assert "No edit operation selected" in str(result[0])
    
    # * Test display formatting for replace_line operation w/ before & after content
    def test_replace_line_operation(self):
        op = EditOperation(
            operation="replace_line",
            line_number=5,
            content="New content",
            original_content="Old content",
            reasoning="Test reasoning",
            confidence=0.85
        )
        
        result = create_operation_display(op)
        assert len(result) > 3  # header, content lines, reasoning
        
        # check operation header
        assert "replace_line" in str(result[0])
        assert "Line: 5" in str(result[1])
        assert "Confidence: 0.85" in str(result[2])
        
        # check content display - should have old and new lines
        content_lines = [str(line) for line in result]
        assert any("Old content" in line for line in content_lines)
        assert any("New content" in line for line in content_lines)
        assert any("Test reasoning" in line for line in content_lines)
    
    # * Test display formatting for replace_range operation w/ start & end lines
    def test_replace_range_operation(self):
        op = EditOperation(
            operation="replace_range",
            line_number=10,
            start_line=10,
            end_line=12,
            content="Range replacement",
            original_content="Original range content",
            confidence=0.92
        )
        
        result = create_operation_display(op)
        content_lines = [str(line) for line in result]
        
        assert any("replace_range" in line for line in content_lines)
        assert any("Lines 10-12" in line for line in content_lines)
        assert any("Range replacement" in line for line in content_lines)
        assert any("Original range content" in line for line in content_lines)
    
    # * Test display formatting for insert_after operation w/ positioning
    def test_insert_after_operation(self):
        op = EditOperation(
            operation="insert_after",
            line_number=8,
            content="Inserted content",
            reasoning="Adding new information"
        )
        
        result = create_operation_display(op)
        content_lines = [str(line) for line in result]
        
        assert any("insert_after" in line for line in content_lines)
        assert any("Insert after line 8" in line for line in content_lines)
        assert any("Inserted content" in line for line in content_lines)
        assert any("Adding new information" in line for line in content_lines)
    
    # * Test display formatting for delete_range operation w/ line ranges
    def test_delete_range_operation(self):
        op = EditOperation(
            operation="delete_range",
            line_number=15,
            start_line=15,
            end_line=17,
            reasoning="Removing outdated content"
        )
        
        result = create_operation_display(op)
        content_lines = [str(line) for line in result]
        
        assert any("delete_range" in line for line in content_lines)
        assert any("Delete lines 15-17" in line for line in content_lines)
        assert any("Removing outdated content" in line for line in content_lines)
    
    # * Test display formatting when confidence value is zero
    def test_operation_without_confidence(self):
        op = EditOperation(
            operation="replace_line",
            line_number=3,
            content="Test content"
        )
        
        result = create_operation_display(op)
        content_lines = [str(line) for line in result]
        
        # confidence should not appear when it's 0.0
        assert not any("Confidence: 0.00" in line for line in content_lines)
    
    # * Test display formatting when reasoning field is empty
    def test_operation_without_reasoning(self):
        op = EditOperation(
            operation="replace_line",
            line_number=3,
            content="Test content"
        )
        
        result = create_operation_display(op)
        content_lines = [str(line) for line in result]
        
        # reasoning section should not appear when empty
        assert not any("Reasoning:" in line for line in content_lines)
    
    # * Test display formatting when original_content is missing
    def test_operation_with_no_original_content(self):
        op = EditOperation(
            operation="replace_line",
            line_number=5,
            content="New content"
        )
        
        result = create_operation_display(op)
        content_lines = [str(line) for line in result]
        
        # should display "[no content]" when original_content is empty
        assert any("[no content]" in line for line in content_lines)


# * Test header layout creation w/ filename & progress display

@patch('src.ui.diff_resolution.diff_display.edit_operations', [])
@patch('src.ui.diff_resolution.diff_display.current_operation_index', 0)
@patch('src.ui.diff_resolution.diff_display.current_filename', "test.txt")
class TestCreateHeaderLayout:
    # * Test header layout when no operations are available
    def test_header_with_no_operations(self):
        with patch('src.ui.diff_resolution.diff_display.edit_operations', []):
            result = create_header_layout()
            # should not raise exception even with empty operations
            assert result is not None
    
    # * Test header layout w/ operation count & progress info
    def test_header_with_operations(self):
        mock_ops = [Mock(), Mock(), Mock()]
        with patch('src.ui.diff_resolution.diff_display.edit_operations', mock_ops):
            with patch('src.ui.diff_resolution.diff_display.current_operation_index', 1):
                with patch('src.ui.diff_resolution.diff_display.current_filename', "resume.docx"):
                    result = create_header_layout()
                    assert result is not None


# * Test footer layout creation w/ approval status summary

@patch('src.ui.diff_resolution.diff_display.edit_operations', [])
@patch('src.ui.diff_resolution.diff_display.current_operation_index', 0)
class TestCreateFooterLayout:
    # * Test footer layout when no operations are processed
    def test_footer_with_no_operations(self):
        result = create_footer_layout()
        assert result is not None
    
    # * Test footer layout w/ approval/rejection/skip counts
    def test_footer_with_processed_operations(self):
        # create mock operations with different statuses
        op1 = Mock()
        op1.status = DiffOp.APPROVE
        op2 = Mock()
        op2.status = DiffOp.REJECT
        op3 = Mock()
        op3.status = DiffOp.SKIP
        
        mock_ops = [op1, op2, op3]
        with patch('src.ui.diff_resolution.diff_display.edit_operations', mock_ops):
            with patch('src.ui.diff_resolution.diff_display.current_operation_index', 3):
                result = create_footer_layout()
                assert result is not None


# * Test menu option diff mapping functionality

@patch('src.ui.diff_resolution.diff_display.current_edit_operation', None)
class TestGetDiffsByOpt:
    # * Test menu option to diff content mapping structure
    def test_get_diffs_by_opt_structure(self):
        result = get_diffs_by_opt()
        
        assert isinstance(result, dict)
        assert "Approve" in result
        assert "Reject" in result
        assert "Skip" in result
        assert "Exit" in result
        
        # all values should be lists of Text objects
        for value in result.values():
            assert isinstance(value, list)
            # the create_operation_display should return at least one Text object
            assert len(value) >= 1


# * Test full screen rendering integration w/ layout components

class TestRenderScreenIntegration:
    @patch('src.ui.diff_resolution.diff_display.options', ["Approve", "Reject", "Skip", "Exit"])
    @patch('src.ui.diff_resolution.diff_display.selected', 0)
    @patch('src.ui.diff_resolution.diff_display.current_edit_operation', None)
    @patch('src.ui.diff_resolution.diff_display.edit_operations', [])
    @patch('src.ui.diff_resolution.diff_display.current_operation_index', 0)
    @patch('src.ui.diff_resolution.diff_display.current_filename', "test.txt")
    # * Test basic screen rendering w/ default state
    def test_render_screen_basic(self):
        # test that render_screen doesn't crash with basic setup
        render_screen()  # should not raise exception
    
    @patch('src.ui.diff_resolution.diff_display.options', ["Approve", "Reject", "Skip", "Exit"])
    @patch('src.ui.diff_resolution.diff_display.selected', 1)
    # * Test screen rendering w/ different menu selection
    def test_render_screen_with_different_selection(self):
        mock_op = EditOperation(
            operation="replace_line",
            line_number=1,
            content="test"
        )
        
        with patch('src.ui.diff_resolution.diff_display.current_edit_operation', mock_op):
            with patch('src.ui.diff_resolution.diff_display.edit_operations', [mock_op]):
                with patch('src.ui.diff_resolution.diff_display.current_operation_index', 0):
                    with patch('src.ui.diff_resolution.diff_display.current_filename', "test.txt"):
                        render_screen()  # should not raise exception


# * Test main display loop initialization & setup

class TestMainDisplayLoopSetup:
    @patch('src.ui.diff_resolution.diff_display.Live')
    @patch('src.ui.diff_resolution.diff_display.readkey')
    # * Test display loop initialization w/ operations & mocked UI
    def test_main_display_loop_initialization(self, mock_readkey, mock_live):
        # setup mocks
        mock_readkey.return_value = '\x1b'  # ESC key to exit immediately
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__.return_value = mock_live_instance
        
        from src.ui.diff_resolution.diff_display import main_display_loop
        
        # create test operations
        test_ops = [
            EditOperation(operation="replace_line", line_number=1, content="test1"),
            EditOperation(operation="replace_line", line_number=2, content="test2")
        ]
        
        # should not raise exception
        try:
            main_display_loop(test_ops, "test_file.txt")
        except SystemExit:
            pass  # expected from ESC key
        
        # verify Live was called
        mock_live.assert_called_once()
    
    # * Test display loop handling when operations list is None
    def test_main_display_loop_with_none_operations(self):
        from src.ui.diff_resolution.diff_display import main_display_loop
        
        # should handle None operations gracefully
        with patch('src.ui.diff_resolution.diff_display.Live') as mock_live:
            with patch('src.ui.diff_resolution.diff_display.readkey') as mock_readkey:
                mock_readkey.return_value = '\x1b'  # ESC to exit
                mock_live_instance = MagicMock()
                mock_live.return_value.__enter__.return_value = mock_live_instance
                
                try:
                    main_display_loop(None, "test.txt")
                except SystemExit:
                    pass  # expected from ESC key