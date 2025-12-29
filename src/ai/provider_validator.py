# src/ai/provider_validator.py
# Runtime provider validation - checks environmental availability (API keys, servers)
#
# * This module complements ModelRegistry (static model metadata) w/ runtime checks:
# *   - ModelRegistry: "Is gpt-4o a valid model string?" (static, intrinsic)
# *   - provider_validator: "Can we call OpenAI right now?" (runtime, environmental)
# * Responsibilities: API key presence, Ollama server availability, error message generation

from __future__ import annotations

from typing import Any

from .cache import AICache
from .models import (
    OPENAI_MODELS,
    CLAUDE_MODELS,
    MODEL_ALIASES,
    resolve_model_alias,
)
from ..config.env_validator import validate_provider_env


# check OpenAI API key availability w/ caching
def check_openai_api_key() -> bool:
    cached = AICache.get_provider_available("openai")
    if cached is not None:
        return cached

    available = validate_provider_env("openai")
    AICache.set_provider_available("openai", available)
    return available


# check Anthropic API key availability w/ caching
def check_anthropic_api_key() -> bool:
    cached = AICache.get_provider_available("anthropic")
    if cached is not None:
        return cached

    available = validate_provider_env("anthropic")
    AICache.set_provider_available("anthropic", available)
    return available


# get cached Ollama models list (returns empty if not cached)
def get_ollama_models() -> list[str]:
    cached = AICache.get_ollama_models()
    if cached is not None:
        return cached
    # if not cached, return empty - Ollama client will populate on first use
    return []


# check if Ollama server is available via cache
def is_ollama_available() -> bool:
    cached = AICache.get_provider_available("ollama")
    return cached is True


# * Validate model & determine its provider (checks API keys & Ollama availability)
def validate_model(model: str) -> tuple[bool, str | None]:
    # resolve alias first
    resolved = resolve_model_alias(model)

    # check static lists first
    if resolved in OPENAI_MODELS:
        if check_openai_api_key():
            return True, "openai"
        else:
            return False, "openai_key_missing"

    if resolved in CLAUDE_MODELS:
        if check_anthropic_api_key():
            return True, "anthropic"
        else:
            return False, "anthropic_key_missing"

    # check Ollama models via cache
    ollama_models = get_ollama_models()
    if resolved in ollama_models:
        return True, "ollama"

    # check if Ollama is available but model not found
    if is_ollama_available() and ollama_models:
        return False, "ollama_model_missing"

    # model not found anywhere
    return False, "model_not_found"


# * Generate comprehensive error message for unavailable models
def get_model_error_message(invalid_model: str) -> str:
    _, provider_status = validate_model(invalid_model)

    if provider_status == "openai_key_missing":
        return f"Model '{invalid_model}' requires OPENAI_API_KEY environment variable to be set."
    elif provider_status == "anthropic_key_missing":
        return f"Model '{invalid_model}' requires ANTHROPIC_API_KEY environment variable to be set."
    elif provider_status == "ollama_model_missing":
        available_ollama = get_ollama_models()
        if available_ollama:
            return f"Model '{invalid_model}' not found in Ollama. Available local models: {', '.join(available_ollama)}"
        else:
            return f"Model '{invalid_model}' not found in Ollama. No local models available."

    # comprehensive model listing
    providers = get_models_by_provider()
    message_parts = [f"Model '{invalid_model}' is not available.\n"]

    for provider_name, info in providers.items():
        if info["available"] and info["models"]:
            message_parts.append(
                f"Available {provider_name.upper()} models: {', '.join(info['models'])}"
            )
        elif info["models"]:
            message_parts.append(
                f"{provider_name.upper()} models (requires {info['requirement']}): {', '.join(info['models'])}"
            )

    # show popular aliases for easier discovery
    alias_examples = [
        "claude-sonnet-4",
        "claude-opus-4",
        "claude-sonnet-3.7",
        "claude-haiku-3.5",
        "gpt4o",
        "gpt5",
    ]
    alias_list = ", ".join(alias_examples)
    message_parts.append(f"Popular aliases: {alias_list}")

    # add recommendation based on what's available
    if is_ollama_available():
        ollama_models = get_ollama_models()
        if ollama_models:
            message_parts.append(f"Recommended local model: {ollama_models[0]}")
    elif check_anthropic_api_key():
        message_parts.append("Recommended: claude-sonnet-4 (high capability)")
    elif check_openai_api_key():
        message_parts.append("Recommended: gpt-5-mini (cost-efficient)")
    else:
        message_parts.append(
            "Recommended: Install Ollama for local models or set API keys for external providers"
        )

    return "\n".join(message_parts)


# * Get all supported models grouped by provider w/ availability status
def get_models_by_provider() -> dict[str, dict[str, Any]]:
    return {
        "openai": {
            "models": OPENAI_MODELS,
            "available": check_openai_api_key(),
            "requirement": "OPENAI_API_KEY environment variable",
        },
        "anthropic": {
            "models": CLAUDE_MODELS,
            "available": check_anthropic_api_key(),
            "requirement": "ANTHROPIC_API_KEY environment variable",
        },
        "ollama": {
            "models": get_ollama_models(),
            "available": is_ollama_available(),
            "requirement": "Ollama server running locally",
        },
    }


# get provider ID for a model
def get_model_provider(model: str) -> str | None:
    valid, provider = validate_model(model)
    return provider if valid else None


# reset all model-related caches (call at start of each CLI invocation)
def reset_model_cache() -> None:
    AICache.invalidate_all()
