# tests/integration/test_interactive_diff_workflow.py
# Integration tests for interactive diff workflow & end-to-end functionality

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.core.constants import EditOperation, DiffOp
from src.cli.commands.dev.display import display


# * Test interactive diff workflow integration & end-to-end functionality

class TestInteractiveDiffWorkflow:
    """Test the complete workflow from command invocation to diff resolution"""
    
    @patch('src.cli.commands.dev.display.get_settings')
    @patch('src.cli.commands.dev.display.main_display_loop')
    # * Test complete flow from dev command to diff display
    def test_dev_command_to_diff_display_integration(self, mock_display_loop, mock_get_settings):
        """Test complete flow from dev command to diff display"""
        # setup mocks
        mock_settings = Mock()
        mock_settings.dev_mode = True
        mock_get_settings.return_value = mock_settings
        
        mock_display_loop.return_value = []
        
        mock_ctx = Mock()
        
        # run the dev command
        display(mock_ctx, help=False)
        
        # verify the flow worked
        mock_get_settings.assert_called_once_with(mock_ctx)
        mock_display_loop.assert_called_once()
        
        # verify sample operations were passed
        call_args = mock_display_loop.call_args[0]
        assert len(call_args) > 0
        assert isinstance(call_args[0], list)
    
    # * Test EditOperation context preservation through workflow
    def test_operation_context_preservation(self):
        """Test that operation context is preserved through workflow"""
        op = EditOperation(
            operation="replace_range",
            line_number=5,
            start_line=5,
            end_line=7,
            content="New content",
            original_content="Old content",
            reasoning="Test reasoning",
            confidence=0.95,
            before_context=["line 3", "line 4"],
            after_context=["line 8", "line 9"]
        )
        
        # verify all context is preserved
        assert op.before_context == ["line 3", "line 4"]
        assert op.after_context == ["line 8", "line 9"]
        assert op.original_content == "Old content"
        assert op.reasoning == "Test reasoning"
        assert op.confidence == 0.95
    
    # * Test EditOperation status modification & transitions
    def test_edit_operation_status_changes(self):
        """Test that EditOperation status can be modified correctly"""
        op = EditOperation(operation="replace_line", line_number=1, content="Test")
        
        # verify default status
        assert op.status == DiffOp.SKIP
        
        # test status transitions
        op.status = DiffOp.APPROVE
        assert op.status == DiffOp.APPROVE
        
        op.status = DiffOp.REJECT
        assert op.status == DiffOp.REJECT
        
        op.status = DiffOp.SKIP
        assert op.status == DiffOp.SKIP
    
    @patch('src.cli.commands.dev.display.get_settings')
    # * Test dev mode requirement enforcement in workflow
    def test_dev_mode_requirement_integration(self, mock_get_settings):
        """Test that dev mode is properly required for display command"""
        mock_settings = Mock()
        mock_settings.dev_mode = False
        mock_get_settings.return_value = mock_settings
        
        mock_ctx = Mock()
        
        # should raise SystemExit when dev mode is disabled
        with pytest.raises(SystemExit) as exc_info:
            display(mock_ctx, help=False)
        
        assert exc_info.value.code == 1
    
    @patch('src.cli.commands.dev.display.get_settings')
    @patch('src.cli.commands.dev.display.main_display_loop')
    # * Test sample operations creation & integration w/ display
    def test_sample_operations_integration(self, mock_display_loop, mock_get_settings):
        """Test that sample operations are properly created and passed"""
        mock_settings = Mock()
        mock_settings.dev_mode = True
        mock_get_settings.return_value = mock_settings
        
        mock_display_loop.return_value = []
        
        mock_ctx = Mock()
        
        display(mock_ctx, help=False)
        
        # verify display loop was called with operations
        mock_display_loop.assert_called_once()
        call_args = mock_display_loop.call_args[0]
        operations = call_args[0]
        
        # verify operations structure
        assert isinstance(operations, list)
        assert len(operations) > 0
        
        for op in operations:
            assert isinstance(op, EditOperation)
            assert hasattr(op, 'operation')
            assert hasattr(op, 'line_number')
            assert hasattr(op, 'content')
            assert hasattr(op, 'reasoning')
            assert hasattr(op, 'confidence')
            assert hasattr(op, 'status')
    
    # * Test DiffOp enum integration w/ EditOperation workflow
    def test_diff_op_enum_integration(self):
        """Test DiffOp enum integration with EditOperation"""
        op = EditOperation(operation="replace_line", line_number=1)
        
        # test all enum values work with EditOperation
        for diff_op in DiffOp:
            op.status = diff_op
            assert op.status == diff_op
            assert op.status.value in ["approve", "reject", "skip"]
    
    @patch('src.ui.diff_resolution.diff_display.console')
    # * Test console integration & proper import handling
    def test_console_integration(self, mock_console):
        """Test that console is properly integrated"""
        from src.ui.diff_resolution.diff_display import render_screen
        
        # should use the console from loom_io
        render_screen()
        
        # verify console is accessible (imported correctly)
        assert mock_console is not None
    
    # * Test EditOperation field validation & default behavior
    def test_edit_operation_field_validation(self):
        """Test EditOperation field validation and defaults"""
        # test minimal creation
        op1 = EditOperation(operation="replace_line", line_number=1)
        assert op1.operation == "replace_line"
        assert op1.line_number == 1
        assert op1.content == ""
        assert op1.confidence == 0.0
        assert op1.status == DiffOp.SKIP
        
        # test full creation
        op2 = EditOperation(
            operation="replace_range",
            line_number=5,
            start_line=5,
            end_line=10,
            content="Full content",
            reasoning="Full reasoning",
            confidence=0.95,
            before_context=["before"],
            after_context=["after"],
            original_content="original"
        )
        
        assert op2.start_line == 5
        assert op2.end_line == 10
        assert op2.content == "Full content"
        assert op2.reasoning == "Full reasoning"
        assert op2.confidence == 0.95
        assert op2.before_context == ["before"]
        assert op2.after_context == ["after"]
        assert op2.original_content == "original"