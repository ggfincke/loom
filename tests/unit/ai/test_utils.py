# tests/unit/ai/test_utils.py
# Unit tests for AI utils - process_json_response & APICallContext

import pytest

from src.ai.utils import (
    APICallContext,
    process_json_response,
    strip_markdown_code_blocks,
)
from src.core.exceptions import AIError


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
        assert result.data == {"edits": [{"type": "replace", "line": 1, "text": "hello"}]}


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
