# tests/unit/core/test_edit_helpers.py
# Unit tests for edit helper functions

import pytest
from src.core.edit_helpers import (
    check_line_exists,
    check_range_exists,
    check_range_usage,
    collect_lines_to_move,
    count_text_lines,
    shift_lines,
    validate_line_number,
    validate_operation_interactions,
    validate_range_bounds,
    validate_required_fields,
    validate_text_field,
    get_operation_line,
    OP_REPLACE_LINE,
    OP_REPLACE_RANGE,
    OP_INSERT_AFTER,
    OP_DELETE_RANGE,
)


@pytest.fixture
def sample_lines():
    return {
        1: "Line 1",
        2: "Line 2",
        3: "Line 3",
        5: "Line 5",  # Gap at line 4
    }


class TestLineExistence:
    def test_check_line_exists_true(self, sample_lines):
        assert check_line_exists(1, sample_lines) is True
        assert check_line_exists(3, sample_lines) is True

    def test_check_line_exists_false(self, sample_lines):
        assert check_line_exists(4, sample_lines) is False
        assert check_line_exists(99, sample_lines) is False

    def test_check_line_exists_empty_dict(self):
        assert check_line_exists(1, {}) is False


class TestRangeExistence:
    def test_check_range_exists_all_present(self, sample_lines):
        exists, missing = check_range_exists(1, 3, sample_lines)
        assert exists is True
        assert missing is None

    def test_check_range_exists_gap_in_middle(self, sample_lines):
        exists, missing = check_range_exists(3, 5, sample_lines)
        assert exists is False
        assert missing == 4

    def test_check_range_exists_start_missing(self, sample_lines):
        exists, missing = check_range_exists(0, 2, sample_lines)
        assert exists is False
        assert missing == 0

    def test_check_range_exists_end_missing(self, sample_lines):
        exists, missing = check_range_exists(1, 99, sample_lines)
        assert exists is False
        assert missing == 4


class TestLineCountCalculation:
    def test_count_text_lines_single(self):
        assert count_text_lines("single line") == 1

    def test_count_text_lines_multiple(self):
        assert count_text_lines("line 1\nline 2\nline 3") == 3

    def test_count_text_lines_empty_no_allow(self):
        assert count_text_lines("") == 0

    def test_count_text_lines_empty_with_allow(self):
        assert count_text_lines("", allow_empty=True) == 1

    def test_count_text_lines_trailing_newline(self):
        assert count_text_lines("line 1\nline 2\n") == 3


class TestLineNumberValidation:
    def test_validate_line_number_valid(self):
        is_valid, error = validate_line_number(5)
        assert is_valid is True
        assert error is None

    def test_validate_line_number_invalid_type(self):
        is_valid, error = validate_line_number("5")
        assert is_valid is False
        assert "'line' must be integer >= 1" in error

    def test_validate_line_number_zero(self):
        is_valid, error = validate_line_number(0)
        assert is_valid is False
        assert "'line' must be integer >= 1" in error

    def test_validate_line_number_negative(self):
        is_valid, error = validate_line_number(-1)
        assert is_valid is False
        assert "'line' must be integer >= 1" in error

    def test_validate_line_number_with_op_index(self):
        is_valid, error = validate_line_number("5", op_index=2)
        assert is_valid is False
        assert "Op 2:" in error


class TestRangeBoundsValidation:
    def test_validate_range_bounds_valid(self):
        is_valid, error = validate_range_bounds(1, 5)
        assert is_valid is True
        assert error is None

    def test_validate_range_bounds_invalid_type_start(self):
        is_valid, error = validate_range_bounds("1", 5)
        assert is_valid is False
        assert "start and end must be integers" in error

    def test_validate_range_bounds_invalid_type_end(self):
        is_valid, error = validate_range_bounds(1, "5")
        assert is_valid is False
        assert "start and end must be integers" in error

    def test_validate_range_bounds_start_less_than_one(self):
        is_valid, error = validate_range_bounds(0, 5)
        assert is_valid is False
        assert "invalid range 0-5" in error

    def test_validate_range_bounds_end_less_than_one(self):
        is_valid, error = validate_range_bounds(1, 0)
        assert is_valid is False
        assert "invalid range 1-0" in error

    def test_validate_range_bounds_start_greater_than_end(self):
        is_valid, error = validate_range_bounds(5, 3)
        assert is_valid is False
        assert "invalid range 5-3" in error

    def test_validate_range_bounds_with_op_index(self):
        is_valid, error = validate_range_bounds(5, 3, op_index=7)
        assert is_valid is False
        assert "Op 7:" in error


class TestRequiredFieldsValidation:
    def test_validate_required_fields_all_present(self):
        op = {"line": 1, "text": "test"}
        is_valid, error = validate_required_fields(
            op, ["line", "text"], "replace_line"
        )
        assert is_valid is True
        assert error is None

    def test_validate_required_fields_one_missing(self):
        op = {"line": 1}
        is_valid, error = validate_required_fields(
            op, ["line", "text"], "replace_line"
        )
        assert is_valid is False
        assert "missing required fields (text)" in error

    def test_validate_required_fields_multiple_missing(self):
        op = {}
        is_valid, error = validate_required_fields(
            op, ["start", "end", "text"], "replace_range"
        )
        assert is_valid is False
        assert "missing required fields" in error
        assert "start" in error
        assert "end" in error
        assert "text" in error

    def test_validate_required_fields_with_op_index(self):
        op = {"line": 1}
        is_valid, error = validate_required_fields(
            op, ["line", "text"], "replace_line", op_index=3
        )
        assert is_valid is False
        assert "Op 3:" in error


class TestTextFieldValidation:
    def test_validate_text_field_valid_string(self):
        is_valid, error = validate_text_field("test text")
        assert is_valid is True
        assert error is None

    def test_validate_text_field_invalid_type(self):
        is_valid, error = validate_text_field(123)
        assert is_valid is False
        assert "'text' must be string" in error

    def test_validate_text_field_newlines_allowed(self):
        is_valid, error = validate_text_field("line 1\nline 2", allow_newlines=True)
        assert is_valid is True
        assert error is None

    def test_validate_text_field_newlines_disallowed(self):
        is_valid, error = validate_text_field("line 1\nline 2", allow_newlines=False)
        assert is_valid is False
        assert "contains newline" in error
        assert "use replace_range" in error

    def test_validate_text_field_with_op_index(self):
        is_valid, error = validate_text_field(123, op_index=5)
        assert is_valid is False
        assert "Op 5:" in error


class TestGetOperationLine:
    def test_get_operation_line_with_line_field(self):
        op = {"line": 42, "text": "test"}
        assert get_operation_line(op) == 42

    def test_get_operation_line_with_start_field(self):
        op = {"start": 10, "end": 15, "text": "test"}
        assert get_operation_line(op) == 10

    def test_get_operation_line_with_both_fields(self):
        # line takes precedence
        op = {"line": 42, "start": 10, "text": "test"}
        assert get_operation_line(op) == 42

    def test_get_operation_line_with_neither_field(self):
        op = {"other": "field"}
        assert get_operation_line(op) == 0


class TestOperationConstants:
    def test_operation_constants_defined(self):
        assert OP_REPLACE_LINE == "replace_line"
        assert OP_REPLACE_RANGE == "replace_range"
        assert OP_INSERT_AFTER == "insert_after"
        assert OP_DELETE_RANGE == "delete_range"


# =============================================================================
# Tests for consolidated helpers (from validation.py & pipeline.py)
# =============================================================================


class TestCheckRangeUsage:
    # * No warnings when range has no prior usage
    def test_no_duplicates(self):
        line_usage = {}
        warnings = check_range_usage(1, 3, line_usage, "replace_range", 0)
        assert warnings == []
        assert line_usage == {1: "replace_range", 2: "replace_range", 3: "replace_range"}

    # * Detects & reports duplicate when range overlaps prior usage
    def test_detects_duplicate(self):
        line_usage = {2: "replace_line"}
        warnings = check_range_usage(1, 3, line_usage, "replace_range", 1)
        assert len(warnings) == 1
        assert "Op 1: duplicate operation on line 2" in warnings[0]

    # * All lines in range marked even when duplicate detected
    def test_marks_all_lines_even_with_duplicate(self):
        line_usage = {2: "replace_line"}
        check_range_usage(1, 3, line_usage, "replace_range", 0)
        assert line_usage == {
            1: "replace_range",
            2: "replace_range",
            3: "replace_range",
        }

    # * Only first duplicate in range is reported
    def test_reports_first_duplicate_only(self):
        line_usage = {2: "replace_line", 3: "replace_line"}
        warnings = check_range_usage(1, 4, line_usage, "delete_range", 2)
        assert len(warnings) == 1
        assert "line 2" in warnings[0]


class TestValidateOperationInteractions:
    # * Warns when insert_after targets a line being deleted
    def test_insert_after_on_deleted_line(self):
        ops = [
            {"op": "delete_range", "start": 5, "end": 10},
            {"op": "insert_after", "line": 7, "text": "new"},
        ]
        warnings = validate_operation_interactions(ops)
        assert len(warnings) == 1
        assert "insert_after on line 7 that is deleted" in warnings[0]

    # * Warns when delete_range overlaps w/ replace_range
    def test_delete_range_overlaps_replace_range(self):
        ops = [
            {"op": "replace_range", "start": 5, "end": 10, "text": "new"},
            {"op": "delete_range", "start": 8, "end": 12},
        ]
        warnings = validate_operation_interactions(ops)
        assert len(warnings) == 1
        assert "delete_range overlaps a replace_range" in warnings[0]

    # * Warns when multiple insert_after target same line
    def test_multiple_insert_after_same_line(self):
        ops = [
            {"op": "insert_after", "line": 5, "text": "first"},
            {"op": "insert_after", "line": 5, "text": "second"},
        ]
        warnings = validate_operation_interactions(ops)
        assert len(warnings) == 1
        assert "multiple insert_after on line 5" in warnings[0]

    # * No warnings when operations don't conflict
    def test_no_conflicts(self):
        ops = [
            {"op": "replace_line", "line": 1, "text": "new"},
            {"op": "insert_after", "line": 3, "text": "added"},
            {"op": "delete_range", "start": 10, "end": 12},
        ]
        warnings = validate_operation_interactions(ops)
        assert warnings == []

    # * No warnings for non-overlapping delete & replace ranges
    def test_non_overlapping_ranges(self):
        ops = [
            {"op": "replace_range", "start": 1, "end": 5, "text": "new"},
            {"op": "delete_range", "start": 10, "end": 15},
        ]
        warnings = validate_operation_interactions(ops)
        assert warnings == []


class TestCollectLinesToMove:
    # * Collects all lines after specified line number
    def test_collects_lines_after(self):
        lines = {1: "a", 2: "b", 3: "c", 5: "e"}
        result = collect_lines_to_move(lines, 2)
        assert (3, "c") in result
        assert (5, "e") in result
        assert len(result) == 2

    # * Returns empty list when no lines after threshold
    def test_empty_result(self):
        lines = {1: "a", 2: "b"}
        result = collect_lines_to_move(lines, 5)
        assert result == []

    # * Result sorted descending for safe deletion
    def test_sorted_descending(self):
        lines = {1: "a", 3: "c", 5: "e", 7: "g"}
        result = collect_lines_to_move(lines, 2)
        line_nums = [k for k, v in result]
        assert line_nums == [7, 5, 3]

    # * Does not include boundary line itself
    def test_excludes_boundary_line(self):
        lines = {1: "a", 2: "b", 3: "c"}
        result = collect_lines_to_move(lines, 2)
        assert (2, "b") not in result
        assert len(result) == 1
        assert (3, "c") in result


class TestShiftLines:
    # * Shifts lines down (positive delta)
    def test_positive_delta(self):
        lines = {1: "a", 2: "b", 3: "c"}
        lines_to_move = [(3, "c"), (2, "b")]  # descending order
        shift_lines(lines, lines_to_move, 2)
        assert lines == {1: "a", 4: "b", 5: "c"}

    # * Shifts lines up (negative delta)
    def test_negative_delta(self):
        lines = {1: "a", 5: "e", 6: "f"}
        lines_to_move = [(6, "f"), (5, "e")]
        shift_lines(lines, lines_to_move, -2)
        assert lines == {1: "a", 3: "e", 4: "f"}

    # * Modifies lines dict in place
    def test_modifies_in_place(self):
        lines = {1: "a", 2: "b"}
        original_id = id(lines)
        lines_to_move = [(2, "b")]
        shift_lines(lines, lines_to_move, 1)
        assert id(lines) == original_id
        assert lines == {1: "a", 3: "b"}

    # * Handles empty lines_to_move gracefully
    def test_empty_lines_to_move(self):
        lines = {1: "a", 2: "b"}
        shift_lines(lines, [], 5)
        assert lines == {1: "a", 2: "b"}

    # * Zero delta results in no change to line positions
    def test_zero_delta(self):
        lines = {1: "a", 2: "b", 3: "c"}
        lines_to_move = [(3, "c"), (2, "b")]
        shift_lines(lines, lines_to_move, 0)
        assert lines == {1: "a", 2: "b", 3: "c"}
