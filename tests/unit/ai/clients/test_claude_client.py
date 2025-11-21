# tests/unit/test_claude_client.py
# Thin tests for Claude client: success normalization & API error raising AIError

import json
import sys
import types
import importlib
import typing as t
import pytest

# provide minimal anthropic module so client import succeeds even if not installed
if "anthropic" not in sys.modules:
    dummy = types.ModuleType("anthropic")

    # placeholder; tests will monkeypatch src module's Anthropic symbol
    class _Placeholder:
        pass

    # cast to Any so Pylance accepts dynamic attribute
    t.cast(t.Any, dummy).Anthropic = _Placeholder
    sys.modules["anthropic"] = dummy

from src.ai.clients import claude_client as cc
from src.core.exceptions import AIError


# describe fake messages surface for Anthropic SDK
class _FakeAnthropicMessages:
    def __init__(
        self, response_text: str | None = None, error: Exception | None = None
    ):
        self._response_text = response_text
        self._error = error

    def create(self, **kwargs):
        if self._error:
            raise self._error

        class _ContentBlock:
            def __init__(self, text):
                self.type = "text"
                self.text = text

        class _Response:
            def __init__(self, text):
                self.content = [_ContentBlock(text)]

        return _Response(self._response_text or "{}")


# describe fake Anthropic client wrapper
class _FakeAnthropic:
    def __init__(
        self, response_text: str | None = None, error: Exception | None = None
    ):
        self.messages = _FakeAnthropicMessages(response_text, error)


# * verify successful result normalization & JSON parsing
def test_claude_success_normalized_result(monkeypatch, mock_env_vars):
    payload = {"sections": [{"name": "SUMMARY"}]}

    # patch Anthropic client constructor to our fake
    monkeypatch.setattr(cc, "Anthropic", lambda: _FakeAnthropic(json.dumps(payload)))

    result = cc.run_generate("Parse resume", model="claude-sonnet-4-20250514")
    assert result.success is True
    assert result.data == payload
    assert result.raw_text
    assert result.json_text


# * verify API error raised as AIError
def test_claude_api_error_raises_aierror(monkeypatch, mock_env_vars):
    # patch Anthropic to raise on create
    monkeypatch.setattr(
        cc, "Anthropic", lambda: _FakeAnthropic(None, RuntimeError("boom"))
    )

    with pytest.raises(AIError):
        cc.run_generate("Parse resume", model="claude-sonnet-4-20250514")
