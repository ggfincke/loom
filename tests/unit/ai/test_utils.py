# tests/unit/ai/test_utils.py
# Unit tests for AI utils - 3-layer response processing

import pytest

from src.ai.utils import (
    APICallContext,
    strip_markdown_code_blocks,
    parse_json,
    validate_and_extract,
    process_ai_response,
    normalize_op_keys,
    normalize_edits_response,
    normalize_section_keys,
    normalize_sections_response,
)
from src.ai.types import GenerateResult
from src.core.exceptions import AIError, JSONParsingError


# * Test APICallContext dataclass


class TestAPICallContext:
    # * Verify create context
    def test_create_context(self):
        ctx = APICallContext(
            raw_text='{"key": "value"}', provider_name="openai", model="gpt-4o"
        )
        assert ctx.raw_text == '{"key": "value"}'
        assert ctx.provider_name == "openai"
        assert ctx.model == "gpt-4o"


# * Test Layer 1: strip_markdown_code_blocks


class TestStripMarkdownCodeBlocks:
    # * Verify strips json code block
    def test_strips_json_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert strip_markdown_code_blocks(text) == '{"key": "value"}'

    # * Verify strips plain code block
    def test_strips_plain_code_block(self):
        text = '```\n{"key": "value"}\n```'
        assert strip_markdown_code_blocks(text) == '{"key": "value"}'

    # * Verify returns plain json
    def test_returns_plain_json(self):
        text = '{"key": "value"}'
        assert strip_markdown_code_blocks(text) == '{"key": "value"}'

    # * Verify strips thinking tokens
    def test_strips_thinking_tokens(self):
        text = '<think>reasoning here</think>\n{"key": "value"}'
        assert strip_markdown_code_blocks(text) == '{"key": "value"}'


# * Test Layer 2: parse_json


class TestParseJson:
    # * Verify parse valid json
    def test_parse_valid_json(self):
        data, json_text, error = parse_json('{"key": "value"}')
        assert data == {"key": "value"}
        assert json_text == '{"key": "value"}'
        assert error == ""

    # * Verify parse json w/ markdown
    def test_parse_json_with_markdown(self):
        data, json_text, error = parse_json('```json\n{"key": "value"}\n```')
        assert data == {"key": "value"}
        assert json_text == '{"key": "value"}'
        assert error == ""

    # * Verify parse invalid json
    def test_parse_invalid_json(self):
        data, json_text, error = parse_json("not json")
        assert data is None
        assert json_text == "not json"
        assert "JSON parsing failed" in error

    # * Verify parse error truncates long text
    def test_parse_error_truncates_long_text(self):
        long_text = "not json " * 50  # >200 chars
        data, json_text, error = parse_json(long_text)
        assert data is None
        assert "..." in error


# * Test Layer 3: validate_and_extract


class TestValidateAndExtract:
    # * Verify valid structure
    def test_valid_structure(self):
        data = {"version": 1, "meta": {"model": "gpt-4o"}, "ops": []}

        result = validate_and_extract(
            data=data,
            raw_text='{"version": 1}',
            json_text='{"version": 1}',
            parse_error="",
            model="gpt-4o",
            context="generation",
        )

        assert result["version"] == 1
        assert "meta" in result
        assert "ops" in result

    # * Verify parse failure raises json parsing error
    def test_parse_failure_raises_json_parsing_error(self):
        with pytest.raises(JSONParsingError) as exc_info:
            validate_and_extract(
                data=None,
                raw_text="not json",
                json_text="not json",
                parse_error="JSON parsing failed",
                model="gpt-4o",
                context="generation",
            )

        error_msg = str(exc_info.value)
        assert "generation" in error_msg
        assert "gpt-4o" in error_msg

    # * Verify non dict raises ai error
    def test_non_dict_raises_ai_error(self):
        with pytest.raises(AIError) as exc_info:
            validate_and_extract(
                data=[],
                raw_text="[]",
                json_text="[]",
                parse_error="",
                model="gpt-4o",
                context="generation",
            )

        assert "not a valid JSON object" in str(exc_info.value)

    # * Verify invalid version raises ai error
    def test_invalid_version_raises_ai_error(self):
        with pytest.raises(AIError) as exc_info:
            validate_and_extract(
                data={"version": 2, "meta": {}, "ops": []},
                raw_text="{}",
                json_text="{}",
                parse_error="",
                model="gpt-4o",
                context="generation",
            )

        assert "Invalid or missing version" in str(exc_info.value)
        assert "expected 1" in str(exc_info.value)

    # * Verify missing required fields
    def test_missing_required_fields(self):
        with pytest.raises(AIError) as exc_info:
            validate_and_extract(
                data={"version": 1, "ops": []},  # missing meta
                raw_text="{}",
                json_text="{}",
                parse_error="",
                model="gpt-4o",
                context="generation",
            )

        assert "missing required fields" in str(exc_info.value)
        assert "meta" in str(exc_info.value)

    # * Verify require single op empty ops
    def test_require_single_op_empty_ops(self):
        with pytest.raises(AIError) as exc_info:
            validate_and_extract(
                data={"version": 1, "meta": {}, "ops": []},
                raw_text="{}",
                json_text="{}",
                parse_error="",
                model="gpt-4o",
                context="PROMPT",
                require_single_op=True,
            )

        assert "empty" in str(exc_info.value).lower()

    # * Verify require single op multiple ops
    def test_require_single_op_multiple_ops(self):
        with pytest.raises(AIError) as exc_info:
            validate_and_extract(
                data={
                    "version": 1,
                    "meta": {},
                    "ops": [{"op": "a"}, {"op": "b"}],
                },
                raw_text="{}",
                json_text="{}",
                parse_error="",
                model="gpt-4o",
                context="PROMPT",
                require_single_op=True,
            )

        assert "exactly one" in str(exc_info.value)

    # * Verify require ops false
    def test_require_ops_false(self):
        result = validate_and_extract(
            data={"version": 1, "meta": {}},  # no ops
            raw_text="{}",
            json_text="{}",
            parse_error="",
            model="gpt-4o",
            context="custom",
            require_ops=False,
        )

        assert result == {"version": 1, "meta": {}}

    # * Verify normalizes short keys
    def test_normalizes_short_keys(self):
        result = validate_and_extract(
            data={"version": 1, "meta": {}, "ops": [{"l": 5, "t": "text"}]},
            raw_text="{}",
            json_text="{}",
            parse_error="",
            model="gpt-4o",
            context="test",
        )

        assert result["ops"][0]["line"] == 5
        assert result["ops"][0]["text"] == "text"


# * Test process_ai_response high-level helper


class TestProcessAiResponse:
    # * Verify end to end success
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

    # * Verify json parsing error propagation
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

    # * Verify ai error propagation
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


# * Test normalize_op_keys helper


class TestNormalizeOpKeys:
    # * Verify expands short keys
    def test_expands_short_keys(self):
        op = {
            "op": "replace_line",
            "l": 5,
            "t": "new text",
            "cur": "old",
            "w": "reason",
        }

        result = normalize_op_keys(op)

        assert result == {
            "op": "replace_line",
            "line": 5,
            "text": "new text",
            "current_snippet": "old",
            "why": "reason",
        }

    # * Verify full keys passthrough
    def test_full_keys_passthrough(self):
        op = {
            "op": "replace_line",
            "line": 5,
            "text": "new text",
        }

        result = normalize_op_keys(op)

        assert result == op

    # * Verify mixed keys
    def test_mixed_keys(self):
        op = {"op": "replace_range", "s": 10, "end": 12, "t": "text"}

        result = normalize_op_keys(op)

        assert result == {"op": "replace_range", "start": 10, "end": 12, "text": "text"}


# * Test normalize_edits_response helper


class TestNormalizeEditsResponse:
    # * Verify normalizes ops
    def test_normalizes_ops(self):
        edits = {
            "version": 1,
            "meta": {},
            "ops": [
                {"op": "replace_line", "l": 5, "t": "text"},
                {"op": "replace_range", "s": 10, "e": 12, "t": "more"},
            ],
        }

        result = normalize_edits_response(edits)

        assert result["ops"][0]["line"] == 5
        assert result["ops"][0]["text"] == "text"
        assert result["ops"][1]["start"] == 10
        assert result["ops"][1]["end"] == 12

    # * Verify handles missing ops
    def test_handles_missing_ops(self):
        edits = {"version": 1, "meta": {}}

        result = normalize_edits_response(edits)

        assert result == {"version": 1, "meta": {}}


# * Test normalize_section_keys helper


class TestNormalizeSectionKeys:
    # * Verify expands short keys
    def test_expands_short_keys(self):
        section = {
            "k": "experience",
            "h": "Work Experience",
            "s": 10,
            "e": 50,
            "c": 0.95,
        }

        result = normalize_section_keys(section)

        assert result == {
            "kind": "experience",
            "heading_text": "Work Experience",
            "start_line": 10,
            "end_line": 50,
            "confidence": 0.95,
        }

    # * Verify subsections array format
    def test_subsections_array_format(self):
        section = {
            "k": "experience",
            "h": "Work",
            "s": 10,
            "e": 50,
            "c": 0.9,
            "sub": [
                ["EXPERIENCE_ITEM", 15, 20],
                ["EXPERIENCE_ITEM", 25, 30, {"company": "Acme"}],
            ],
        }

        result = normalize_section_keys(section)

        assert "subsections" in result
        assert len(result["subsections"]) == 2
        assert result["subsections"][0] == {
            "name": "EXPERIENCE_ITEM",
            "start_line": 15,
            "end_line": 20,
        }


# * Test normalize_sections_response helper


class TestNormalizeSectionsResponse:
    # * Verify normalizes all sections
    def test_normalizes_all_sections(self):
        data = {
            "sections": [
                {"k": "summary", "h": "Summary", "s": 1, "e": 5, "c": 0.9},
                {"k": "experience", "h": "Experience", "s": 10, "e": 50, "c": 0.95},
            ],
        }

        result = normalize_sections_response(data)

        assert result["sections"][0]["kind"] == "summary"
        assert result["sections"][1]["kind"] == "experience"

    # * Verify handles missing sections
    def test_handles_missing_sections(self):
        data = {"notes": "no sections"}

        result = normalize_sections_response(data)

        assert result == {"notes": "no sections"}
