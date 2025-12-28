# src/ai/clients/factory.py
# AI client factory for routing to appropriate provider based on model

from __future__ import annotations

from typing import Callable, Type

from ..provider_validator import validate_model, get_model_error_message
from ..models import ModelRegistry
from ..types import GenerateResult
from .base import BaseClient


# lazy client factory for OpenAI (tests can monkeypatch this)
def _get_openai_client_class() -> Type[BaseClient]:
    from .openai_client import OpenAIClient

    return OpenAIClient

# lazy client factory for Anthropic (tests can monkeypatch this)
def _get_anthropic_client_class() -> Type[BaseClient]:
    from .claude_client import ClaudeClient

    return ClaudeClient

# lazy client factory for Ollama (tests can monkeypatch this)
def _get_ollama_client_class() -> Type[BaseClient]:
    from .ollama_client import OllamaClient

    return OllamaClient

# * Registry mapping provider IDs to client factory functions
CLIENT_REGISTRY: dict[str, Callable[[], Type[BaseClient]]] = {
    "openai": _get_openai_client_class,
    "anthropic": _get_anthropic_client_class,
    "ollama": _get_ollama_client_class,
}

# * Generate JSON response using appropriate AI client based on model
def run_generate(prompt: str, model: str) -> GenerateResult:
    # validate model & determine provider
    valid, provider = validate_model(model)

    if not valid:
        error_msg = get_model_error_message(model)
        return GenerateResult(success=False, error=error_msg)

    # resolve alias to full model name
    resolved_model = ModelRegistry.resolve_alias(model)

    # get client factory from registry
    client_factory = CLIENT_REGISTRY.get(provider)  # type: ignore[arg-type]
    if client_factory is None:
        return GenerateResult(success=False, error=f"Unknown provider: {provider}")

    # instantiate client & run generation
    client_class = client_factory()
    client = client_class()
    return client.run_generate(prompt, resolved_model)
