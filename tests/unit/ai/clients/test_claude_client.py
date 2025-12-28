# tests/unit/ai/clients/test_claude_client.py
# Unit tests for Claude (Anthropic) client functionality

import json
import sys
import types
import pytest
from unittest.mock import patch, Mock
import os

# Provide minimal anthropic module so client import succeeds even if not installed
if "anthropic" not in sys.modules:
    dummy = types.ModuleType("anthropic")

    class _Placeholder:
        pass

    dummy.Anthropic = _Placeholder  # type: ignore
    sys.modules["anthropic"] = dummy

from src.ai.clients.claude_client import ClaudeClient
from src.ai.types import GenerateResult
from src.core.exceptions import AIError, ConfigurationError

# * Helper function to run generate using client directly (no more module-level API)
def _run_generate(prompt: str, model: str) -> GenerateResult:
    client = ClaudeClient()
    return client.run_generate(prompt, model)

# * Fake Anthropic response objects for testing
class _FakeContentBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text

class _FakeResponse:
    def __init__(self, text: str):
        self.content = [_FakeContentBlock(text)]

class _FakeMessages:
    def __init__(
        self, response_text: str | None = None, error: Exception | None = None
    ):
        self._response_text = response_text
        self._error = error

    def create(self, **kwargs):
        if self._error:
            raise self._error
        return _FakeResponse(self._response_text or "{}")

class _FakeAnthropic:
    def __init__(
        self, response_text: str | None = None, error: Exception | None = None
    ):
        self.messages = _FakeMessages(response_text, error)

# * Test successful result normalization & JSON parsing
@patch("anthropic.Anthropic")
@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
# * Verify claude success normalized result
def test_claude_success_normalized_result(mock_anthropic_class):
    payload = {"sections": [{"name": "SUMMARY"}]}

    mock_anthropic_class.return_value = _FakeAnthropic(json.dumps(payload))

    result = _run_generate("Parse resume", "claude-sonnet-4-20250514")
    assert result.success is True
    assert result.data == payload
    assert result.raw_text
    assert result.json_text

# * Test API error raised as AIError (caught by base class, returns error result)
@patch("anthropic.Anthropic")
@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
# * Verify claude api error returns error result
def test_claude_api_error_returns_error_result(mock_anthropic_class):
    mock_anthropic_class.return_value = _FakeAnthropic(None, RuntimeError("boom"))

    result = _run_generate("Parse resume", "claude-sonnet-4-20250514")
    assert result.success is False
    assert "Anthropic API error" in result.error

# * Test missing API key returns error result
@patch.dict(os.environ, {}, clear=True)
# * Verify claude missing api key returns error result
def test_claude_missing_api_key_returns_error_result():
    result = _run_generate("Test prompt", "claude-sonnet-4-20250514")

    assert result.success is False
    assert "ANTHROPIC_API_KEY" in result.error or "anthropic" in result.error.lower()

# * Test markdown code block stripping
@patch("anthropic.Anthropic")
@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
# * Verify claude strips markdown code blocks
def test_claude_strips_markdown_code_blocks(mock_anthropic_class):
    payload = {"result": "test"}
    markdown_response = f"```json\n{json.dumps(payload)}\n```"

    mock_anthropic_class.return_value = _FakeAnthropic(markdown_response)

    result = _run_generate("Test prompt", "claude-sonnet-4-20250514")

    assert result.success is True
    assert result.raw_text == markdown_response
    assert result.json_text == json.dumps(payload)
    assert result.data == payload

# * Test ClaudeClient class directly
class TestClaudeClientClass:

    @patch.dict(os.environ, {}, clear=True)
    # * Verify validate credentials missing key
    def test_validate_credentials_missing_key(self):
        client = ClaudeClient()
        with pytest.raises(ConfigurationError):
            client.validate_credentials()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    # * Verify validate credentials w/ key
    def test_validate_credentials_with_key(self):
        client = ClaudeClient()
        # should not raise
        client.validate_credentials()

    # * Verify provider name
    def test_provider_name(self):
        client = ClaudeClient()
        assert client.provider_name == "anthropic"
