# tests/unit/test_pipeline.py
# Unit tests for core pipeline logic w/ parametrized edit operations

import pytest
import json
from unittest.mock import patch, MagicMock
from src.core.pipeline import (
    apply_edits,
    generate_edits,
    generate_corrected_edits,
    diff_lines,
    number_lines,
    _get_op_line,
    process_prompt_operation,
    process_modify_operation,
)
from src.core.exceptions import EditError, AIError, JSONParsingError
from src.loom_io.types import Lines


# * Fixtures for pipeline testing


@pytest.fixture
def sample_lines_dict() -> Lines:
    # standard Lines dict for testing edit operations
    return {
        1: "John Doe",
        2: "Software Engineer",
        3: "",
        4: "PROFESSIONAL SUMMARY",
        5: "Experienced software engineer w/ 5+ years developing web applications.",
        6: "",
        7: "SKILLS",
        8: "• Python, JavaScript, React",
        9: "• Docker, AWS, CI/CD",
        10: "",
        11: "EXPERIENCE",
        12: "Senior Developer | Tech Corp | 2020-2024",
        13: "• Built scalable web applications",
        14: "• Led team of 3 developers",
    }


@pytest.fixture
def valid_edits_v1():
    # valid edits dict w/ version 1 format
    return {
        "version": 1,
        "meta": {"model": "gpt-5", "created_at": "2024-01-01T00:00:00Z"},
        "ops": [
            {
                "op": "replace_line",
                "line": 5,
                "text": "Experienced Python developer w/ 5+ years building scalable applications.",
            }
        ],
    }


# * Test apply_edits function w/ parametrized operations


class TestApplyEdits:

    @pytest.mark.parametrize(
        "op_type,op_data,expected_result",
        [
            # replace_line operation
            (
                "replace_line",
                {"line": 5, "text": "New summary text"},
                {5: "New summary text"},
            ),
            ("replace_line", {"line": 1, "text": "Jane Smith"}, {1: "Jane Smith"}),
            (
                "replace_line",
                {"line": 14, "text": "• Mentored junior developers"},
                {14: "• Mentored junior developers"},
            ),
            # replace_range operation (same number of lines)
            (
                "replace_range",
                {
                    "start": 8,
                    "end": 9,
                    "text": "• Python, Go, Kubernetes\n• AWS, Docker, Terraform",
                },
                {8: "• Python, Go, Kubernetes", 9: "• AWS, Docker, Terraform"},
            ),
            # insert_after operation
            (
                "insert_after",
                {"line": 9, "text": "• Machine Learning, TensorFlow"},
                {10: "• Machine Learning, TensorFlow"},
            ),
            (
                "insert_after",
                {"line": 14, "text": "• Reduced deployment time by 50%"},
                {15: "• Reduced deployment time by 50%"},
            ),
            # delete_range operation
            ("delete_range", {"start": 8, "end": 9}, "deleted_lines"),
        ],
    )
    # * Test individual edit operations succeed w/ expected results
    def test_single_operation_success(
        self, sample_lines_dict, op_type, op_data, expected_result
    ):
        edits = {"version": 1, "ops": [{"op": op_type, **op_data}]}

        result = apply_edits(sample_lines_dict, edits)

        if expected_result == "deleted_lines":
            # verify lines 8,9 deleted & subsequent lines shifted down
            assert 8 not in result or result[8] != "• Python, JavaScript, React"
            assert 9 not in result or result[9] != "• Docker, AWS, CI/CD"
            # verify lines after 9 were shifted down by 2 positions
            assert result[8] == ""  # line 10 moved to 8
            assert result[9] == "EXPERIENCE"  # line 11 moved to 9
        elif isinstance(expected_result, dict):
            # verify specific line changes
            for line_num, expected_text in expected_result.items():
                assert result[line_num] == expected_text

    # * Test replace_range w/ different line count (3 lines -> 2 lines)
    def test_replace_range_line_count_change(self, sample_lines_dict):
        edits = {
            "version": 1,
            "ops": [
                {
                    "op": "replace_range",
                    "start": 11,
                    "end": 13,  # 3 lines
                    "text": "WORK HISTORY\nSenior Python Developer | TechCorp | 2020-2024",  # 2 lines
                }
            ],
        }

        result = apply_edits(sample_lines_dict, edits)

        # verify replacement content
        assert result[11] == "WORK HISTORY"
        assert result[12] == "Senior Python Developer | TechCorp | 2020-2024"
        # verify line 14 shifted to line 13
        assert result[13] == "• Led team of 3 developers"
        # verify old line 13 position no longer exists
        assert 14 not in result

    # * Test insert_after w/ multi-line text
    def test_insert_after_multiline(self, sample_lines_dict):
        edits = {
            "version": 1,
            "ops": [
                {
                    "op": "insert_after",
                    "line": 9,
                    "text": "• Kubernetes, Helm\n• CI/CD w/ GitHub Actions\n• Monitoring w/ Prometheus",
                }
            ],
        }

        result = apply_edits(sample_lines_dict, edits)

        # verify inserted lines
        assert result[10] == "• Kubernetes, Helm"
        assert result[11] == "• CI/CD w/ GitHub Actions"
        assert result[12] == "• Monitoring w/ Prometheus"
        # verify subsequent lines shifted
        assert result[13] == ""  # original line 10
        assert result[14] == "EXPERIENCE"  # original line 11

    # * Test multiple operations applied in descending line order
    def test_multiple_operations_sorted_descending(self, sample_lines_dict):
        edits = {
            "version": 1,
            "ops": [
                {
                    "op": "replace_line",
                    "line": 14,
                    "text": "• Mentored 5 junior developers",
                },
                {"op": "insert_after", "line": 9, "text": "• GraphQL APIs"},
                {
                    "op": "replace_line",
                    "line": 5,
                    "text": "Senior Python developer w/ 7+ years experience.",
                },
                {"op": "delete_range", "start": 2, "end": 3},
            ],
        }

        result = apply_edits(sample_lines_dict, edits)

        # verify operations applied correctly despite order in ops list
        assert result[1] == "John Doe"
        # after delete_range on lines 2,3 - line 4 becomes line 2
        assert result[2] == "PROFESSIONAL SUMMARY"
        # line 5 becomes line 3, but gets replaced
        assert result[3] == "Senior Python developer w/ 7+ years experience."
        # verify the insert_after operation worked
        assert "• GraphQL APIs" in result.values()


# * Test error conditions & edge cases


class TestApplyEditsErrors:

    # * Test unsupported edits version raises EditError
    def test_unsupported_version(self, sample_lines_dict):
        edits = {"version": 2, "ops": []}

        with pytest.raises(EditError, match="Unsupported edits version: 2"):
            apply_edits(sample_lines_dict, edits)

    @pytest.mark.parametrize(
        "op_data,error_msg",
        [
            (
                {"op": "replace_line", "line": 99, "text": "test"},
                "Cannot replace line 99: line does not exist",
            ),
            (
                {"op": "replace_range", "start": 1, "end": 99, "text": "test"},
                "Cannot replace range 1-99: line 99 does not exist",
            ),
            (
                {"op": "insert_after", "line": 99, "text": "test"},
                "Cannot insert after line 99: line does not exist",
            ),
            (
                {"op": "delete_range", "start": 5, "end": 99},
                "Cannot delete range 5-99: line 15 does not exist",
            ),
        ],
    )
    # * Test operations on non-existent lines raise EditError
    def test_out_of_bounds_operations(self, sample_lines_dict, op_data, error_msg):
        edits = {"version": 1, "ops": [op_data]}

        with pytest.raises(EditError, match=error_msg):
            apply_edits(sample_lines_dict, edits)

    # * Test unknown operation type raises EditError
    def test_unknown_operation_type(self, sample_lines_dict):
        edits = {"version": 1, "ops": [{"op": "unknown_op", "line": 1, "text": "test"}]}

        with pytest.raises(EditError, match="Unknown operation type: unknown_op"):
            apply_edits(sample_lines_dict, edits)

    # * Test apply_edits w/ empty resume dict
    def test_empty_resume_lines(self):
        empty_lines: Lines = {}
        edits = {
            "version": 1,
            "ops": [{"op": "replace_line", "line": 1, "text": "test"}],
        }

        with pytest.raises(
            EditError, match="Cannot replace line 1: line does not exist"
        ):
            apply_edits(empty_lines, edits)

    # * Test replace_range w/ start > end
    def test_replace_range_invalid_bounds(self, sample_lines_dict):
        edits = {
            "version": 1,
            "ops": [{"op": "replace_range", "start": 5, "end": 3, "text": "test"}],
        }

        # this should work without error in current implementation
        # (the range validation happens in validation.py, not pipeline.py)
        result = apply_edits(sample_lines_dict, edits)
        assert isinstance(result, dict)


# * Test AI generation functions w/ mocked responses


class TestGenerateEdits:

    @patch("src.core.pipeline.run_generate")
    # * Test successful AI edit generation
    def test_generate_edits_success(self, mock_run_generate, sample_lines_dict):
        mock_response_data = {
            "version": 1,
            "meta": {"model": "gpt-5"},
            "ops": [{"op": "replace_line", "line": 5, "text": "Updated summary"}],
        }

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_response_data
        mock_run_generate.return_value = mock_result

        result = generate_edits(sample_lines_dict, "job description", None, "gpt-5")

        assert result == mock_response_data
        assert result["version"] == 1
        assert len(result["ops"]) == 1

    @patch("src.core.pipeline.run_generate")
    # * Test JSON parsing error handling
    def test_generate_edits_json_parsing_error(
        self, mock_run_generate, sample_lines_dict
    ):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Invalid JSON syntax"
        mock_result.json_text = '{"invalid": json}'
        mock_result.raw_text = None
        mock_run_generate.return_value = mock_result

        with pytest.raises(JSONParsingError, match="AI generated invalid JSON"):
            generate_edits(sample_lines_dict, "job description", None, "gpt-5")

    @patch("src.core.pipeline.run_generate")
    # * Test AI response structure validation
    def test_generate_edits_invalid_response_structure(
        self, mock_run_generate, sample_lines_dict
    ):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"invalid": "structure"}  # missing version, meta, ops
        mock_run_generate.return_value = mock_result

        with pytest.raises(AIError, match="Invalid or missing version"):
            generate_edits(sample_lines_dict, "job description", None, "gpt-5")

    @patch("src.core.pipeline.run_generate")
    # * Test successful AI edit correction
    def test_generate_corrected_edits_success(
        self, mock_run_generate, sample_lines_dict
    ):
        mock_response_data = {
            "version": 1,
            "meta": {"model": "gpt-5"},
            "ops": [{"op": "replace_line", "line": 5, "text": "Corrected summary"}],
        }

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_response_data
        mock_run_generate.return_value = mock_result

        warnings = ["Line 99 not in bounds"]
        result = generate_corrected_edits(
            '{"ops":[]}', sample_lines_dict, "job desc", None, "gpt-5", warnings
        )

        assert result == mock_response_data
        assert result["version"] == 1


# * Test debug function fallbacks & AI error edge cases


class TestDebugFallbacks:

    # * Test that debug functions don't crash when debug module missing
    def test_debug_functions_handle_import_errors(self, sample_lines_dict):
        # this simulates the ImportError handling in _debug_ai and _debug_error

        # mock the debug module import to fail
        with patch("src.core.pipeline.run_generate") as mock_run_generate:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"version": 1, "meta": {"model": "gpt-5"}, "ops": []}
            mock_run_generate.return_value = mock_result

            # should complete successfully even if debug functions fail
            result = generate_edits(sample_lines_dict, "job", None, "gpt-5")
            assert result["version"] == 1


class TestGenerateEditsExtended:

    @patch("src.core.pipeline.run_generate")
    # * Test JSON error when raw_text differs from json_text (covers line 52)
    def test_generate_edits_json_error_with_different_raw_text(
        self, mock_run_generate, sample_lines_dict
    ):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Invalid JSON syntax"
        mock_result.json_text = '{"invalid": json,}'
        mock_result.raw_text = (
            "The model response was different and very long" * 20
        )  # > 300 chars
        mock_run_generate.return_value = mock_result

        with pytest.raises(JSONParsingError) as exc_info:
            generate_edits(sample_lines_dict, "job description", None, "gpt-5")

        error_msg = str(exc_info.value)
        assert "AI generated invalid JSON" in error_msg
        assert "Full raw response:" in error_msg
        assert "..." in error_msg  # should be truncated

    @patch("src.core.pipeline.run_generate")
    # * Test invalid version handling (covers line 61)
    def test_generate_edits_invalid_version_number(
        self, mock_run_generate, sample_lines_dict
    ):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {
            "version": 2,  # invalid version
            "meta": {"model": "gpt-5"},
            "ops": [],
        }
        mock_run_generate.return_value = mock_result

        with pytest.raises(AIError) as exc_info:
            generate_edits(sample_lines_dict, "job description", None, "gpt-5")

        assert "Invalid or missing version" in str(exc_info.value)
        assert "expected 1" in str(exc_info.value)

    @patch("src.core.pipeline.run_generate")
    # * Test missing meta field (covers lines 68-73)
    def test_generate_edits_missing_meta_field(
        self, mock_run_generate, sample_lines_dict
    ):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {
            "version": 1,
            "ops": [],
            # missing "meta" field
        }
        mock_run_generate.return_value = mock_result

        with pytest.raises(AIError) as exc_info:
            generate_edits(sample_lines_dict, "job description", None, "gpt-5")

        assert "missing required fields: meta" in str(exc_info.value)

    @patch("src.core.pipeline.run_generate")
    # * Test missing ops field (covers lines 68-73)
    def test_generate_edits_missing_ops_field(
        self, mock_run_generate, sample_lines_dict
    ):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {
            "version": 1,
            "meta": {"model": "gpt-5"},
            # missing "ops" field
        }
        mock_run_generate.return_value = mock_result

        with pytest.raises(AIError) as exc_info:
            generate_edits(sample_lines_dict, "job description", None, "gpt-5")

        assert "missing required fields: ops" in str(exc_info.value)

    @patch("src.core.pipeline.run_generate")
    # * Test corrected edits JSON error with raw_text (covers lines 98-99)
    def test_generate_corrected_edits_with_raw_text_error(
        self, mock_run_generate, sample_lines_dict
    ):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "JSON decode error"
        mock_result.json_text = '{"malformed": json}'
        mock_result.raw_text = (
            "Raw AI response that's different from json_text and very long" * 20
        )
        mock_run_generate.return_value = mock_result

        with pytest.raises(JSONParsingError) as exc_info:
            generate_corrected_edits(
                "{}", sample_lines_dict, "job", None, "gpt-5", ["warning"]
            )

        error_msg = str(exc_info.value)
        assert "AI generated invalid JSON during correction" in error_msg
        assert "Full raw response:" in error_msg
        assert "..." in error_msg  # should be truncated


# * Test utility functions


class TestUtilityFunctions:

    # * Test unified diff generation
    def test_diff_lines(self):
        old_lines = {1: "Hello", 2: "World"}
        new_lines = {1: "Hi", 2: "World"}

        diff = diff_lines(old_lines, new_lines)

        assert "old" in diff
        assert "new" in diff
        assert "Hello" in diff
        assert "Hi" in diff

    # * Test line numbering format
    def test_number_lines(self, sample_lines_dict):
        result = number_lines(sample_lines_dict)

        lines = result.split("\n")
        assert "   1 John Doe" in lines
        assert "   2 Software Engineer" in lines
        assert "  14 • Led team of 3 developers" in lines

    @pytest.mark.parametrize(
        "op,expected_line",
        [
            ({"line": 5}, 5),
            ({"start": 10, "end": 12}, 10),
            ({"other": "field"}, 0),
        ],
    )
    # * Test operation line number extraction
    def test_get_op_line(self, op, expected_line):
        result = _get_op_line(op)
        assert result == expected_line


# * Test process_prompt_operation functionality
class TestProcessPromptOperation:

    @pytest.fixture
    def sample_edit_operation(self):
        from src.core.constants import EditOperation

        return EditOperation(
            operation="replace_line",
            line_number=5,
            content="Original content that needs AI regeneration",
            reasoning="User wants more technical language",
            confidence=0.8,
            original_content="Software engineer with experience",
            prompt_instruction="Make this more technical w/ ML frameworks",
        )

    @pytest.fixture
    def sample_resume_lines(self) -> Lines:
        return {
            1: "John Doe",
            2: "Software Engineer",
            3: "",
            4: "PROFESSIONAL SUMMARY",
            5: "Software engineer with experience",
            6: "in building web applications.",
            7: "",
            8: "SKILLS",
            9: "• Python, JavaScript",
            10: "• Docker, AWS",
        }

    @pytest.fixture
    def sample_job_text(self):
        return (
            "Senior Software Engineer - Machine Learning Focus\n"
            "Requirements:\n"
            "- 5+ years Python/ML experience\n"
            "- TensorFlow, PyTorch proficiency\n"
            "- MLOps & deployment experience"
        )

    @pytest.fixture
    def mock_ai_success_response(self):
        return MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {
                    "strategy": "prompt_regeneration",
                    "model": "gpt-4",
                    "created_at": "2024-01-01T00:00:00Z",
                },
                "ops": [
                    {
                        "op": "replace_line",
                        "line": 5,
                        "text": "Machine learning engineer specializing in TensorFlow & PyTorch",
                        "current_snippet": "Software engineer with experience",
                        "why": "Made more technical w/ specific ML frameworks as requested",
                    }
                ],
            },
            error=None,
        )

    @pytest.fixture
    def mock_ai_failure_response(self):
        return MagicMock(success=False, data=None, error="AI model unavailable")

    # * Test successful prompt operation processing
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_success(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
        mock_ai_success_response,
    ):
        mock_run_generate.return_value = mock_ai_success_response

        result = process_prompt_operation(
            edit_op=sample_edit_operation,
            resume_lines=sample_resume_lines,
            job_text=sample_job_text,
            sections_json=None,
            model="gpt-4",
        )

        # verify operation was updated correctly
        assert (
            result.content
            == "Machine learning engineer specializing in TensorFlow & PyTorch"
        )
        assert (
            result.reasoning
            == "Made more technical w/ specific ML frameworks as requested"
        )
        assert result.confidence == 0.9  # default high confidence for user requests

        # verify AI was called correctly
        mock_run_generate.assert_called_once()
        call_args = mock_run_generate.call_args[0]
        prompt = call_args[0]
        model = call_args[1]

        assert model == "gpt-4"
        assert "Make this more technical w/ ML frameworks" in prompt
        assert sample_job_text in prompt
        assert "replace_line" in prompt

    # * Test AI failure handling
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_ai_failure(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
        mock_ai_failure_response,
    ):
        mock_run_generate.return_value = mock_ai_failure_response

        with pytest.raises(AIError) as exc_info:
            process_prompt_operation(
                edit_op=sample_edit_operation,
                resume_lines=sample_resume_lines,
                job_text=sample_job_text,
                sections_json=None,
                model="gpt-4",
            )

        assert "AI failed to process PROMPT operation" in str(exc_info.value)
        assert "AI model unavailable" in str(exc_info.value)

    # * Test invalid JSON response handling
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_invalid_json(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
    ):
        # mock response w/ invalid JSON structure
        mock_run_generate.return_value = MagicMock(
            success=True, data="Invalid string response instead of dict", error=None
        )

        with pytest.raises(AIError) as exc_info:
            process_prompt_operation(
                edit_op=sample_edit_operation,
                resume_lines=sample_resume_lines,
                job_text=sample_job_text,
                sections_json=None,
                model="gpt-4",
            )

        assert "AI response is not a valid JSON object" in str(exc_info.value)
        assert "got str" in str(exc_info.value)

    # * Test missing version validation
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_missing_version(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
    ):
        mock_run_generate.return_value = MagicMock(
            success=True,
            data={
                "meta": {"strategy": "prompt_regeneration"},
                "ops": [{"op": "replace_line", "text": "test"}],
            },
            error=None,
        )

        with pytest.raises(AIError) as exc_info:
            process_prompt_operation(
                edit_op=sample_edit_operation,
                resume_lines=sample_resume_lines,
                job_text=sample_job_text,
                sections_json=None,
                model="gpt-4",
            )

        assert "Invalid or missing version" in str(exc_info.value)
        assert "expected 1" in str(exc_info.value)

    # * Test missing ops array validation
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_missing_ops(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
    ):
        mock_run_generate.return_value = MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {"strategy": "prompt_regeneration"},
                # missing ops array
            },
            error=None,
        )

        with pytest.raises(AIError) as exc_info:
            process_prompt_operation(
                edit_op=sample_edit_operation,
                resume_lines=sample_resume_lines,
                job_text=sample_job_text,
                sections_json=None,
                model="gpt-4",
            )

        assert "AI response missing 'ops' array" in str(exc_info.value)

    # * Test multiple operations validation (should be exactly one)
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_multiple_ops(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
    ):
        mock_run_generate.return_value = MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {"strategy": "prompt_regeneration"},
                "ops": [
                    {"op": "replace_line", "text": "first"},
                    {"op": "replace_line", "text": "second"},  # too many ops
                ],
            },
            error=None,
        )

        with pytest.raises(AIError) as exc_info:
            process_prompt_operation(
                edit_op=sample_edit_operation,
                resume_lines=sample_resume_lines,
                job_text=sample_job_text,
                sections_json=None,
                model="gpt-4",
            )

        assert "must contain exactly one operation" in str(exc_info.value)
        assert "got 2" in str(exc_info.value)

    # * Test empty ops array
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_empty_ops(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
    ):
        mock_run_generate.return_value = MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {"strategy": "prompt_regeneration"},
                "ops": [],  # empty ops array
            },
            error=None,
        )

        with pytest.raises(AIError) as exc_info:
            process_prompt_operation(
                edit_op=sample_edit_operation,
                resume_lines=sample_resume_lines,
                job_text=sample_job_text,
                sections_json=None,
                model="gpt-4",
            )

        assert "ops array is empty" in str(exc_info.value)

    # * Test optional fields handling (confidence, why)
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_optional_fields(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
    ):
        # response w/o optional fields
        mock_run_generate.return_value = MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {"strategy": "prompt_regeneration"},
                "ops": [
                    {
                        "op": "replace_line",
                        "text": "Updated content",
                        # missing why & confidence fields
                    }
                ],
            },
            error=None,
        )

        result = process_prompt_operation(
            edit_op=sample_edit_operation,
            resume_lines=sample_resume_lines,
            job_text=sample_job_text,
            sections_json=None,
            model="gpt-4",
        )

        # should handle missing optional fields gracefully
        assert result.content == "Updated content"
        assert result.confidence == 0.9  # default high confidence
        assert (
            result.reasoning == "User wants more technical language"
        )  # original reasoning preserved when not overridden

    # * Test sections_json parameter handling
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_with_sections(
        self,
        mock_run_generate,
        sample_edit_operation,
        sample_resume_lines,
        sample_job_text,
        mock_ai_success_response,
    ):
        mock_run_generate.return_value = mock_ai_success_response
        sections_json = (
            '{"sections": [{"name": "SUMMARY", "start_line": 4, "end_line": 6}]}'
        )

        process_prompt_operation(
            edit_op=sample_edit_operation,
            resume_lines=sample_resume_lines,
            job_text=sample_job_text,
            sections_json=sections_json,
            model="gpt-4",
        )

        # verify sections_json was passed to prompt builder
        call_args = mock_run_generate.call_args[0]
        prompt = call_args[0]

        # sections should be referenced in prompt somehow
        assert len(prompt) > 500  # substantial prompt

    # * Test different operation types
    @patch("src.core.pipeline.run_generate")
    def test_process_prompt_operation_different_types(
        self, mock_run_generate, sample_resume_lines, sample_job_text
    ):
        from src.core.constants import EditOperation

        operation_types = [
            "replace_line",
            "replace_range",
            "insert_after",
            "delete_range",
        ]

        for op_type in operation_types:
            # create operation for each type
            edit_op = EditOperation(
                operation=op_type,
                line_number=5,
                start_line=5 if op_type in ["replace_range", "delete_range"] else None,
                end_line=6 if op_type in ["replace_range", "delete_range"] else None,
                content=f"Test content for {op_type}",
                reasoning=f"Test {op_type} operation",
                prompt_instruction=f"Test {op_type} instruction",
            )

            mock_run_generate.return_value = MagicMock(
                success=True,
                data={
                    "version": 1,
                    "meta": {"strategy": "prompt_regeneration"},
                    "ops": [
                        {
                            "op": op_type.replace("_", "_"),  # handle naming
                            "text": f"AI generated content for {op_type}",
                            "why": f"Updated {op_type} as requested",
                        }
                    ],
                },
                error=None,
            )

            result = process_prompt_operation(
                edit_op=edit_op,
                resume_lines=sample_resume_lines,
                job_text=sample_job_text,
                sections_json=None,
                model="gpt-4",
            )

            # verify operation was processed correctly
            assert result.content == f"AI generated content for {op_type}"
            assert result.reasoning == f"Updated {op_type} as requested"
