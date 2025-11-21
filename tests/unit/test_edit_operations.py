# tests/unit/test_edit_operations.py
# Unit tests for EditOperation dataclass & DiffOp enum functionality

import pytest
from dataclasses import asdict
from src.core.constants import EditOperation, DiffOp


# * Test DiffOp enum values & behavior


class TestDiffOp:
    # * Test all DiffOp enum values have correct string representations
    def test_diff_op_values(self):
        assert DiffOp.APPROVE.value == "approve"
        assert DiffOp.REJECT.value == "reject"
        assert DiffOp.SKIP.value == "skip"
        assert DiffOp.MODIFY.value == "modify"
        assert DiffOp.PROMPT.value == "prompt"

    # * Test enum membership & count validation
    def test_diff_op_enum_members(self):
        assert len(DiffOp) == 5
        assert DiffOp.APPROVE in DiffOp
        assert DiffOp.REJECT in DiffOp
        assert DiffOp.SKIP in DiffOp
        assert DiffOp.MODIFY in DiffOp
        assert DiffOp.PROMPT in DiffOp


# * Test EditOperation dataclass functionality & field validation


class TestEditOperation:
    # * Test minimal EditOperation creation w/ default values
    def test_minimal_edit_operation(self):
        op = EditOperation(operation="replace_line", line_number=5)
        assert op.operation == "replace_line"
        assert op.line_number == 5
        assert op.content == ""
        assert op.start_line is None
        assert op.end_line is None
        assert op.reasoning == ""
        assert op.confidence == 0.0
        assert op.status == DiffOp.SKIP
        assert op.before_context == []
        assert op.after_context == []
        assert op.original_content == ""

    # * Test replace_line operation w/ full field population
    def test_replace_line_operation(self):
        op = EditOperation(
            operation="replace_line",
            line_number=10,
            content="New line content",
            reasoning="Updated for clarity",
            confidence=0.95,
            original_content="Old line content",
        )
        assert op.operation == "replace_line"
        assert op.line_number == 10
        assert op.content == "New line content"
        assert op.reasoning == "Updated for clarity"
        assert op.confidence == 0.95
        assert op.original_content == "Old line content"

    # * Test replace_range operation w/ start & end line validation
    def test_replace_range_operation(self):
        op = EditOperation(
            operation="replace_range",
            line_number=5,
            start_line=5,
            end_line=7,
            content="Multi-line\ncontent replacement",
            reasoning="Expand section detail",
            confidence=0.88,
        )
        assert op.operation == "replace_range"
        assert op.start_line == 5
        assert op.end_line == 7
        assert op.content == "Multi-line\ncontent replacement"

    # * Test insert_after operation w/ line positioning
    def test_insert_after_operation(self):
        op = EditOperation(
            operation="insert_after",
            line_number=12,
            content="• New bullet point",
            reasoning="Add missing skill",
            confidence=0.92,
        )
        assert op.operation == "insert_after"
        assert op.line_number == 12
        assert op.content == "• New bullet point"

    # * Test delete_range operation w/ empty content validation
    def test_delete_range_operation(self):
        op = EditOperation(
            operation="delete_range",
            line_number=20,
            start_line=20,
            end_line=22,
            reasoning="Remove outdated information",
            confidence=0.85,
        )
        assert op.operation == "delete_range"
        assert op.start_line == 20
        assert op.end_line == 22
        assert op.content == ""  # delete operations have no content

    # * Test status field assignment & DiffOp enum integration
    def test_status_assignment(self):
        op = EditOperation(operation="replace_line", line_number=1)

        # test default status
        assert op.status == DiffOp.SKIP

        # test status changes
        op.status = DiffOp.APPROVE
        assert op.status == DiffOp.APPROVE

        op.status = DiffOp.REJECT
        assert op.status == DiffOp.REJECT

    # * Test before_context & after_context list field handling
    def test_context_lists(self):
        before_ctx = ["line 1", "line 2", "line 3"]
        after_ctx = ["line 5", "line 6"]

        op = EditOperation(
            operation="replace_line",
            line_number=4,
            before_context=before_ctx,
            after_context=after_ctx,
        )

        assert op.before_context == before_ctx
        assert op.after_context == after_ctx
        assert len(op.before_context) == 3
        assert len(op.after_context) == 2

    # * Test confidence field w/ valid numeric ranges
    def test_confidence_bounds(self):
        # test valid confidence values
        op1 = EditOperation(operation="replace_line", line_number=1, confidence=0.0)
        assert op1.confidence == 0.0

        op2 = EditOperation(operation="replace_line", line_number=1, confidence=1.0)
        assert op2.confidence == 1.0

        op3 = EditOperation(operation="replace_line", line_number=1, confidence=0.75)
        assert op3.confidence == 0.75

    # * Test dataclass serialization to dict format
    def test_dataclass_serialization(self):
        op = EditOperation(
            operation="replace_line",
            line_number=5,
            content="Test content",
            reasoning="Test reasoning",
            confidence=0.9,
            status=DiffOp.APPROVE,
            before_context=["line 1"],
            after_context=["line 2"],
            original_content="Original",
        )

        # test conversion to dict
        op_dict = asdict(op)
        assert op_dict["operation"] == "replace_line"
        assert op_dict["line_number"] == 5
        assert op_dict["content"] == "Test content"
        assert op_dict["status"] == DiffOp.APPROVE
        assert op_dict["before_context"] == ["line 1"]

    # * Test all supported operation types are valid
    def test_operation_types(self):
        # test all supported operation types
        operations = ["replace_line", "replace_range", "insert_after", "delete_range"]

        for op_type in operations:
            op = EditOperation(operation=op_type, line_number=1)
            assert op.operation == op_type

    # * Test empty string & None value handling
    def test_empty_strings_and_none_values(self):
        op = EditOperation(
            operation="replace_line",
            line_number=1,
            content="",
            reasoning="",
            original_content="",
        )

        assert op.content == ""
        assert op.reasoning == ""
        assert op.original_content == ""
        assert op.start_line is None
        assert op.end_line is None

    # * Test large line number values for edge cases
    def test_large_line_numbers(self):
        op = EditOperation(operation="replace_line", line_number=999999)
        assert op.line_number == 999999

        op_range = EditOperation(
            operation="replace_range", line_number=1000, start_line=1000, end_line=2000
        )
        assert op_range.start_line == 1000
        assert op_range.end_line == 2000

    # * Test multiline content handling w/ newline characters
    def test_multiline_content(self):
        multiline_content = """Line 1 of content
Line 2 of content
Line 3 of content"""

        op = EditOperation(
            operation="replace_range", line_number=1, content=multiline_content
        )

        assert "\n" in op.content
        assert op.content.count("\n") == 2
        assert "Line 1 of content" in op.content
        assert "Line 3 of content" in op.content
