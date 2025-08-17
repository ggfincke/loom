# tests/unit/test_ollama_client_branches.py
# Unit tests for Ollama client branches by monkeypatching the SDK surface

import json
import sys
import types
import importlib
import pytest

# ensure dummy ollama module exists before importing client
if "ollama" not in sys.modules:
    sys.modules["ollama"] = types.ModuleType("ollama")

from src.ai.clients import ollama_client as oc


class _FakeModel:
    def __init__(self, name: str) -> None:
        self.model = name


class _ListResponse:
    def __init__(self, models):
        self.models = models


@pytest.fixture
def patch_ollama(monkeypatch):
    # safely monkeypatch list/chat on imported module
    yield monkeypatch


# * verify success path & code-fence stripping
def test_run_generate_success_with_code_fence(patch_ollama):
    # simulate available model and successful chat response with JSON code fence
    patch_ollama.setattr(oc.ollama, "list", lambda: _ListResponse([_FakeModel("llama3.2")]))

    def _chat(model, messages, options):
        payload = {"sections": [{"name": "SUMMARY"}]}
        return {"message": {"content": f"```json\n{json.dumps(payload)}\n```"}}

    patch_ollama.setattr(oc.ollama, "chat", _chat)

    result = oc.run_generate("Parse this resume", model="llama3.2")
    assert result.success is True
    assert result.data == {"sections": [{"name": "SUMMARY"}]}
    assert result.json_text.strip().startswith("{")  # code fence stripped


# * verify model-not-found branch lists available models
def test_run_generate_model_not_found_lists_available(patch_ollama):
    # model requested is not in available list
    patch_ollama.setattr(oc.ollama, "list", lambda: _ListResponse([_FakeModel("llama3.1")]))

    result = oc.run_generate("Prompt", model="llama3.2")
    assert result.success is False
    assert "not found" in result.error.lower()
    assert "available models" in result.error.lower() or "available" in result.error.lower()


# * verify network error on availability check handled
def test_run_generate_network_error_on_availability_check(patch_ollama):
    # simulate connection failure when checking availability
    def _raise():
        raise ConnectionError("Connection refused")

    patch_ollama.setattr(oc.ollama, "list", _raise)

    result = oc.run_generate("Prompt", model="llama3.2")
    assert result.success is False
    assert "connection" in result.error.lower() or "ollama" in result.error.lower()


# * verify thinking tokens are stripped in json_text
def test_run_generate_strips_thinking_tokens(patch_ollama):
    patch_ollama.setattr(oc.ollama, "list", lambda: _ListResponse([_FakeModel("llama3.2")]))

    def _chat(model, messages, options):
        content = "<think>some chain of thought</think> {\n  \"sections\": []\n}"
        return {"message": {"content": content}}

    patch_ollama.setattr(oc.ollama, "chat", _chat)

    result = oc.run_generate("Prompt", model="llama3.2")
    assert result.success is True
    # ensure thinking tokens removed in json_text but present in raw_text
    assert "<think>" not in result.json_text
    assert "</think>" not in result.json_text
    assert "<think>" in result.raw_text
