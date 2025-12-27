# tests/unit/ai/clients/test_ollama_client.py
# Unit tests for Ollama client branches by monkeypatching the SDK surface

import json
import sys
import types
import pytest

# ensure dummy ollama module exists before importing client
if "ollama" not in sys.modules:
    ollama_module = types.ModuleType("ollama")
    setattr(ollama_module, "list", None)
    setattr(ollama_module, "chat", None)
    sys.modules["ollama"] = ollama_module

from src.ai.clients.ollama_client import (
    run_generate,
    OllamaClient,
    _get_client,
    reset_cache,
)
from src.ai.cache import AICache
from src.core.exceptions import AIError


class _FakeModel:
    def __init__(self, name: str) -> None:
        self.model = name


class _ListResponse:
    def __init__(self, models):
        self.models = models


@pytest.fixture(autouse=True)
def reset_ollama_cache():
    # Reset cache before each test to avoid stale data.
    reset_cache()
    AICache.invalidate_all()
    yield
    reset_cache()
    AICache.invalidate_all()


# * Verify success path & code-fence stripping
def test_run_generate_success_with_code_fence(monkeypatch):
    # patch ollama.list to return available model
    monkeypatch.setattr("ollama.list", lambda: _ListResponse([_FakeModel("llama3.2")]))

    def _chat(**_kwargs):
        payload = {"sections": [{"name": "SUMMARY"}]}
        return {"message": {"content": f"```json\n{json.dumps(payload)}\n```"}}

    monkeypatch.setattr("ollama.chat", _chat)

    result = run_generate("Parse this resume", model="llama3.2")
    assert result.success is True
    assert result.data == {"sections": [{"name": "SUMMARY"}]}
    assert result.json_text.strip().startswith("{")  # code fence stripped


# * Verify model-not-found branch lists available models
def test_run_generate_model_not_found_lists_available(monkeypatch):
    # model requested is not in available list
    monkeypatch.setattr("ollama.list", lambda: _ListResponse([_FakeModel("llama3.1")]))

    result = run_generate("Prompt", model="llama3.2")

    assert result.success is False
    error_msg = result.error.lower()
    assert "not found" in error_msg
    assert "available" in error_msg or "llama3.1" in error_msg


# * Verify network error on availability check handled
def test_run_generate_network_error_on_availability_check(monkeypatch):
    def _raise():
        raise ConnectionError("Connection refused")

    monkeypatch.setattr("ollama.list", _raise)

    result = run_generate("Prompt", model="llama3.2")

    assert result.success is False
    error_msg = result.error.lower()
    assert "connection" in error_msg or "ollama" in error_msg


# * Verify thinking tokens are stripped in json_text
def test_run_generate_strips_thinking_tokens(monkeypatch):
    monkeypatch.setattr("ollama.list", lambda: _ListResponse([_FakeModel("llama3.2")]))

    def _chat(**_kwargs):
        content = '<think>some chain of thought</think> {\n  "sections": []\n}'
        return {"message": {"content": content}}

    monkeypatch.setattr("ollama.chat", _chat)

    result = run_generate("Prompt", model="llama3.2")
    assert result.success is True
    # ensure thinking tokens removed in json_text but present in raw_text
    assert "<think>" not in result.json_text
    assert "</think>" not in result.json_text
    assert "<think>" in result.raw_text


# * Verify API error during chat is handled
def test_run_generate_api_error_during_chat(monkeypatch):
    monkeypatch.setattr("ollama.list", lambda: _ListResponse([_FakeModel("llama3.2")]))

    def _chat(**_kwargs):
        raise RuntimeError("Model crashed")

    monkeypatch.setattr("ollama.chat", _chat)

    result = run_generate("Prompt", model="llama3.2")

    assert result.success is False
    assert "Ollama API error" in result.error


# * Test OllamaClient class directly
class TestOllamaClientClass:

    # * Verify provider name
    def test_provider_name(self):
        client = OllamaClient()
        assert client.provider_name == "ollama"

    # * Verify validate credentials always passes
    def test_validate_credentials_always_passes(self):
        client = OllamaClient()
        # Ollama doesn't require credentials - should not raise
        client.validate_credentials()
