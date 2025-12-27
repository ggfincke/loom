# src/ai/models.py
# AI model catalog & aliases for Loom CLI (OpenAI, Anthropic & Ollama)
#
# This module provides:
# - Model name catalogs (OPENAI_MODELS, CLAUDE_MODELS, etc.)
# - Model aliases for user-friendly short names
# - Default model configuration per provider
# - Alias resolution
#
# Provider validation logic is in provider_validator.py

from typing import List, Optional


# * Supported OpenAI models
OPENAI_MODELS: List[str] = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4o",
    "gpt-4o-mini",
]

# * Supported Claude models (Anthropic)
CLAUDE_MODELS: List[str] = [
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]

# * Combined supported models list (static models only, not Ollama)
SUPPORTED_MODELS: List[str] = OPENAI_MODELS + CLAUDE_MODELS

# * Model aliases for user-friendly short names
MODEL_ALIASES: dict[str, str] = {
    # Claude 4 series
    "claude-opus-4.1": "claude-opus-4-1-20250805",
    "claude-opus-4": "claude-opus-4-20250514",
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    # Claude 3 series
    "claude-sonnet-3.7": "claude-3-7-sonnet-20250219",
    "claude-haiku-3.5": "claude-3-5-haiku-20241022",
    "claude-haiku-3": "claude-3-haiku-20240307",
    # OpenAI variations (already short, but add common variations)
    "gpt4o": "gpt-4o",
    "gpt4": "gpt-4o",
    "gpt5": "gpt-5",
    "gpt-5m": "gpt-5-mini",
    "gpt-5n": "gpt-5-nano",
}

# * Model categories for user guidance
MODEL_CATEGORIES: dict[str, List[str]] = {
    "latest": [
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "claude-opus-4-1-20250805",
        "claude-sonnet-4-20250514",
    ],
    "cost_effective": [
        "gpt-5-mini",
        "gpt-5-nano",
        "claude-3-5-haiku-20241022",
        "claude-3-haiku-20240307",
    ],
    "high_capability": [
        "gpt-5",
        "claude-opus-4-1-20250805",
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
    ],
}

# * Default models by provider - single source of truth
DEFAULT_MODELS_BY_PROVIDER: dict[str, str] = {
    "openai": "gpt-5-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "ollama": "llama3.2",
}

# * Model metadata - descriptions & provider info for UI display
# Maps model name -> (provider, description)
MODEL_METADATA: dict[str, tuple[str, str]] = {
    # OpenAI models
    "gpt-5": ("openai", "GPT-5 (latest, most capable)"),
    "gpt-5-mini": ("openai", "GPT-5 Mini (latest generation, cost-efficient)"),
    "gpt-5-nano": ("openai", "GPT-5 Nano (fastest, ultra-low latency)"),
    "gpt-4o": ("openai", "GPT-4o (multimodal, high capability)"),
    "gpt-4o-mini": ("openai", "GPT-4o Mini (fast, cost-effective)"),
    # Claude models
    "claude-opus-4-1-20250805": ("anthropic", "Claude Opus 4.1 (latest, most capable)"),
    "claude-opus-4-20250514": ("anthropic", "Claude Opus 4 (high capability)"),
    "claude-sonnet-4-20250514": ("anthropic", "Claude Sonnet 4 (balanced)"),
    "claude-3-7-sonnet-20250219": ("anthropic", "Claude 3.7 Sonnet (fast, capable)"),
    "claude-3-5-haiku-20241022": (
        "anthropic",
        "Claude 3.5 Haiku (fast, cost-effective)",
    ),
    "claude-3-haiku-20240307": ("anthropic", "Claude 3 Haiku (fastest, economical)"),
}


def get_model_description(model: str) -> str:
    # Get human-readable description for a model.
    if model in MODEL_METADATA:
        return MODEL_METADATA[model][1]
    return model


def resolve_model_alias(model: str) -> str:
    # Resolve model alias to full model name.
    # first check if it's already a valid full model name
    if model in SUPPORTED_MODELS:
        return model

    # then check if it's an alias
    if model in MODEL_ALIASES:
        return MODEL_ALIASES[model]

    # return original if no alias found (may be Ollama model)
    return model


def get_default_model(provider: Optional[str] = None) -> str:
    # Get the default model for a provider.
    if provider is None:
        # global default is OpenAI
        return DEFAULT_MODELS_BY_PROVIDER["openai"]
    return DEFAULT_MODELS_BY_PROVIDER.get(
        provider, DEFAULT_MODELS_BY_PROVIDER["openai"]
    )


def get_provider_for_model(model: str) -> Optional[str]:
    # Get the provider ID for a known static model. Note: This only checks static model lists. For dynamic validation including Ollama, use provider_validator.validate_model().
    if model in OPENAI_MODELS:
        return "openai"
    if model in CLAUDE_MODELS:
        return "anthropic"
    return None
