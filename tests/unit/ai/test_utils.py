# tests/unit/ai/test_utils.py
# Unit tests for AI utils - process_json_response & APICallContext

import pytest

from src.ai.utils import (
    APICallContext,
    process_json_response,
    strip_markdown_code_blocks,
    convert_result_to_dict,
    validate_edits_structure,
    process_ai_response,
)
from src.ai.types import GenerateResult
from src.core.exceptions import AIError, JSONParsingError


# * Test APICallContext dataclass


class TestAPICallContext:
    def test_create_context(self):
        ctx = APICallContext(
            raw_text='{"key": "value"}', provider_name="openai", model="gpt-4o"
        )
        assert ctx.raw_text == '{"key": "value"}'
        assert ctx.provider_name == "openai"
        assert ctx.model == "gpt-4o"


# * Test process_json_response


class TestProcessJsonResponse:
    # * Test successful JSON parsing
    def test_success_valid_json(self):
        def mock_api_call(prompt: str, model: str) -> APICallContext:
            return APICallContext(
                raw_text='{"result": "success"}', provider_name="openai", model=model
            )

        result = process_json_response(mock_api_call, "test prompt", "gpt-4o")

        assert result.success is True
        assert result.data == {"result": "success"}
        assert result.raw_text == '{"result": "success"}'
        assert result.json_text == '{"result": "success"}'
        assert result.error == ""

    # * Test JSON parsing w/ markdown code block stripping
    def test_strips_markdown_code_blocks(self):
        def mock_api_call(prompt: str, model: str) -> APICallContext:
            return APICallContext(
                raw_text='```json\n{"result": "success"}\n```',
                provider_name="claude",
                model=model,
            )

        result = process_json_response(mock_api_call, "test prompt", "claude-sonnet-4")

        assert result.success is True
        assert result.data == {"result": "success"}
        assert result.raw_text == '```json\n{"result": "success"}\n```'
        assert result.json_text == '{"result": "success"}'

    # * Test error includes model name & truncation
    def test_error_includes_model_and_truncation(self):
        long_invalid_json = "not json " * 50  # >200 chars

        def mock_api_call(prompt: str, model: str) -> APICallContext:
            return APICallContext(
                raw_text=long_invalid_json, provider_name="ollama", model=model
            )

        result = process_json_response(mock_api_call, "test prompt", "llama3.2")

        assert result.success is False
        assert result.data is None
        assert "llama3.2" in result.error
        assert "JSON parsing failed" in result.error
        assert "..." in result.error  # truncated
        assert len(result.error) < len(long_invalid_json) + 100

    # * Test short invalid JSON error not truncated
    def test_short_error_not_truncated(self):
        short_invalid = "not json"

        def mock_api_call(prompt: str, model: str) -> APICallContext:
            return APICallContext(
                raw_text=short_invalid, provider_name="openai", model=model
            )

        result = process_json_response(mock_api_call, "test prompt", "gpt-4o")

        assert result.success is False
        assert "..." not in result.error
        assert "not json" in result.error

    # * Test API error propagates (not wrapped as GenerateResult)
    def test_api_error_propagates(self):
        def mock_api_call(prompt: str, model: str) -> APICallContext:
            raise AIError("Connection failed")

        with pytest.raises(AIError, match="Connection failed"):
            process_json_response(mock_api_call, "test prompt", "gpt-4o")

    # * Test complex nested JSON
    def test_complex_nested_json(self):
        nested_json = '{"edits": [{"type": "replace", "line": 1, "text": "hello"}]}'

        def mock_api_call(prompt: str, model: str) -> APICallContext:
            return APICallContext(
                raw_text=nested_json, provider_name="openai", model=model
            )

        result = process_json_response(mock_api_call, "test prompt", "gpt-4o")

        assert result.success is True
        assert result.data == {
            "edits": [{"type": "replace", "line": 1, "text": "hello"}]
        }


# * Test convert_result_to_dict helper


class TestConvertResultToDict:
    # * Test successful conversion
    def test_successful_conversion(self):
        result = GenerateResult(
            success=True,
            data={"version": 1, "meta": {}, "ops": []},
            raw_text='{"version": 1}',
            json_text='{"version": 1}',
        )

        data = convert_result_to_dict(result, "gpt-4o", "generation")

        assert data == {"version": 1, "meta": {}, "ops": []}

    # * Test raises JSONParsingError on failure
    def test_raises_on_failure(self):
        result = GenerateResult(
            success=False,
            raw_text="not json",
            json_text="not json",
            error="JSON parsing failed: Expecting value",
        )

        with pytest.raises(JSONParsingError) as exc_info:
            convert_result_to_dict(result, "gpt-4o", "generation")

        error_msg = str(exc_info.value)
        assert "generation" in error_msg
        assert "gpt-4o" in error_msg
        assert "not json" in error_msg

    # * Test snippet truncation for long JSON
    def test_snippet_truncation(self):
        long_json = "invalid\n" * 10  # >5 lines to trigger truncation
        result = GenerateResult(
            success=False,
            raw_text=long_json,
            json_text=long_json,
            error="JSON parsing failed",
        )

        with pytest.raises(JSONParsingError) as exc_info:
            convert_result_to_dict(result, "gpt-4o", "correction")

        error_msg = str(exc_info.value)
        assert "..." in error_msg  # should have truncation indicator

    # * Test includes raw response when different from JSON text
    def test_includes_raw_response(self):
        result = GenerateResult(
            success=False,
            raw_text="```json\ninvalid\n```",
            json_text="invalid",
            error="JSON parsing failed",
        )

        with pytest.raises(JSONParsingError) as exc_info:
            convert_result_to_dict(result, "gpt-4o", "generation")

        error_msg = str(exc_info.value)
        assert "Full raw response" in error_msg


# * Test validate_edits_structure helper


class TestValidateEditsStructure:
    # * Test valid structure passes
    def test_valid_structure(self):
        data = {"version": 1, "meta": {"model": "gpt-4o"}, "ops": []}

        result = validate_edits_structure(data, "gpt-4o", "generation")

        assert result == data

    # * Test non-dict raises AIError
    def test_non_dict_raises_error(self):
        with pytest.raises(AIError) as exc_info:
            validate_edits_structure([], "gpt-4o", "generation")

        assert "not a valid JSON object" in str(exc_info.value)
        assert "list" in str(exc_info.value)

    # * Test missing/invalid version raises AIError
    def test_invalid_version(self):
        with pytest.raises(AIError) as exc_info:
            validate_edits_structure(
                {"version": 2, "meta": {}, "ops": []}, "gpt-4o", "generation"
            )

        assert "Invalid or missing version" in str(exc_info.value)
        assert "expected 1" in str(exc_info.value)

    # * Test missing version raises AIError
    def test_missing_version(self):
        with pytest.raises(AIError) as exc_info:
            validate_edits_structure(
                {"meta": {}, "ops": []}, "gpt-4o", "generation"
            )

        assert "Invalid or missing version" in str(exc_info.value)

    # * Test missing meta field raises AIError
    def test_missing_meta(self):
        with pytest.raises(AIError) as exc_info:
            validate_edits_structure({"version": 1, "ops": []}, "gpt-4o", "generation")

        assert "missing required fields" in str(exc_info.value)
        assert "meta" in str(exc_info.value)

    # * Test missing ops field raises AIError
    def test_missing_ops(self):
        with pytest.raises(AIError) as exc_info:
            validate_edits_structure(
                {"version": 1, "meta": {}}, "gpt-4o", "generation"
            )

        assert "missing required fields" in str(exc_info.value)
        assert "ops" in str(exc_info.value)

    # * Test require_single_op validation - valid
    def test_require_single_op_valid(self):
        data = {
            "version": 1,
            "meta": {},
            "ops": [{"op": "replace_line", "line": 1, "text": "new text"}],
        }

        result = validate_edits_structure(
            data, "gpt-4o", "PROMPT operation", require_single_op=True
        )

        assert result == data

    # * Test require_single_op validation - empty ops
    def test_require_single_op_empty_ops(self):
        data = {"version": 1, "meta": {}, "ops": []}

        with pytest.raises(AIError) as exc_info:
            validate_edits_structure(
                data, "gpt-4o", "PROMPT operation", require_single_op=True
            )

        assert "empty" in str(exc_info.value).lower()

    # * Test require_single_op validation - multiple ops
    def test_require_single_op_multiple_ops(self):
        data = {
            "version": 1,
            "meta": {},
            "ops": [
                {"op": "replace_line", "line": 1, "text": "text1"},
                {"op": "replace_line", "line": 2, "text": "text2"},
            ],
        }

        with pytest.raises(AIError) as exc_info:
            validate_edits_structure(
                data, "gpt-4o", "PROMPT operation", require_single_op=True
            )

        assert "exactly one" in str(exc_info.value)
        assert "got 2" in str(exc_info.value)

    # * Test require_ops=False allows missing ops
    def test_require_ops_false(self):
        data = {"version": 1, "meta": {}}

        result = validate_edits_structure(
            data, "gpt-4o", "custom", require_ops=False
        )

        assert result == data

    # * Test context appears in error messages
    def test_context_in_error(self):
        with pytest.raises(AIError) as exc_info:
            validate_edits_structure(
                {"version": 2, "meta": {}, "ops": []}, "gpt-4o", "correction"
            )

        assert "during correction" in str(exc_info.value)


# * Test process_ai_response high-level helper


class TestProcessAiResponse:
    # * Test end-to-end success
    def test_end_to_end_success(self):
        result = GenerateResult(
            success=True,
            data={"version": 1, "meta": {"model": "gpt-4o"}, "ops": []},
            raw_text='{"version": 1}',
            json_text='{"version": 1}',
        )

        data = process_ai_response(result, "gpt-4o", "generation")

        assert data["version"] == 1
        assert "meta" in data
        assert "ops" in data

    # * Test JSONParsingError propagation
    def test_json_parsing_error_propagation(self):
        result = GenerateResult(
            success=False,
            raw_text="not json",
            json_text="not json",
            error="JSON parsing failed",
        )

        with pytest.raises(JSONParsingError) as exc_info:
            process_ai_response(result, "gpt-4o", "generation")

        assert "generation" in str(exc_info.value)

    # * Test AIError propagation
    def test_ai_error_propagation(self):
        result = GenerateResult(
            success=True,
            data={"version": 2, "meta": {}, "ops": []},  # wrong version
            raw_text="{}",
            json_text="{}",
        )

        with pytest.raises(AIError) as exc_info:
            process_ai_response(result, "gpt-4o", "generation")

        assert "Invalid or missing version" in str(exc_info.value)

    # * Test require_single_op parameter
    def test_require_single_op_parameter(self):
        result = GenerateResult(
            success=True,
            data={"version": 1, "meta": {}, "ops": []},  # empty ops
            raw_text="{}",
            json_text="{}",
        )

        with pytest.raises(AIError) as exc_info:
            process_ai_response(
                result, "gpt-4o", "PROMPT operation", require_single_op=True
            )

        assert "empty" in str(exc_info.value).lower()

    # * Test log flags forwarded
    def test_log_flags_forwarded(self, caplog):
        result = GenerateResult(
            success=True,
            data={"version": 1, "meta": {}, "ops": []},
            raw_text="{}",
            json_text="{}",
        )

        process_ai_response(
            result,
            "gpt-4o",
            "generation",
            log_version_debug=True,
            log_structure=True,
        )

        # Just verify it doesn't raise - logging tests are in integration tests


# * Test strip_markdown_code_blocks helper


class TestStripMarkdownCodeBlocks:
    def test_strips_json_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert strip_markdown_code_blocks(text) == '{"key": "value"}'

    def test_strips_plain_code_block(self):
        text = '```\n{"key": "value"}\n```'
        assert strip_markdown_code_blocks(text) == '{"key": "value"}'

    def test_returns_plain_json(self):
        text = '{"key": "value"}'
        assert strip_markdown_code_blocks(text) == '{"key": "value"}'

    def test_strips_thinking_tokens(self):
        text = '<think>reasoning here</think>\n{"key": "value"}'
        assert strip_markdown_code_blocks(text) == '{"key": "value"}'
