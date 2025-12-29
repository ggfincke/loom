# src/ai/models.py
# AI model catalog, aliases & registry for OpenAI, Anthropic & Ollama providers

from __future__ import annotations

# * Supported OpenAI models
OPENAI_MODELS: list[str] = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4o",
    "gpt-4o-mini",
]

# * Supported Claude models (Anthropic)
CLAUDE_MODELS: list[str] = [
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]

# * Combined supported models list (static models only, not Ollama)
SUPPORTED_MODELS: list[str] = OPENAI_MODELS + CLAUDE_MODELS

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
MODEL_CATEGORIES: dict[str, list[str]] = {
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
    if model in MODEL_METADATA:
        return MODEL_METADATA[model][1]
    return model


def resolve_model_alias(model: str) -> str:
    # first check if it's already a valid full model name
    if model in SUPPORTED_MODELS:
        return model
    # then check if it's an alias
    if model in MODEL_ALIASES:
        return MODEL_ALIASES[model]
    # return original if no alias found (may be Ollama model)
    return model


def get_default_model(provider: str | None = None) -> str:
    if provider is None:
        # global default is OpenAI
        return DEFAULT_MODELS_BY_PROVIDER["openai"]
    return DEFAULT_MODELS_BY_PROVIDER.get(
        provider, DEFAULT_MODELS_BY_PROVIDER["openai"]
    )


def get_provider_for_model(model: str) -> str | None:
    # ? Note: This only checks static model lists. For dynamic validation including Ollama, use provider_validator.validate_model()
    if model in OPENAI_MODELS:
        return "openai"
    if model in CLAUDE_MODELS:
        return "anthropic"
    return None


# * Centralized model validation & resolution registry
class ModelRegistry:
    # resolve alias to full model name
    @classmethod
    def resolve_alias(cls, model: str) -> str:
        if model in SUPPORTED_MODELS:
            return model
        return MODEL_ALIASES.get(model, model)

    # get provider ID for known static model
    @classmethod
    def get_provider(cls, model: str) -> str | None:
        if model in OPENAI_MODELS:
            return "openai"
        if model in CLAUDE_MODELS:
            return "anthropic"
        return None

    # check if model is in static lists (OpenAI or Anthropic)
    @classmethod
    def is_static_model(cls, model: str) -> bool:
        return model in SUPPORTED_MODELS

    # get default model for provider
    @classmethod
    def get_default(cls, provider: str | None = None) -> str:
        if provider is None:
            return DEFAULT_MODELS_BY_PROVIDER["openai"]
        return DEFAULT_MODELS_BY_PROVIDER.get(
            provider, DEFAULT_MODELS_BY_PROVIDER["openai"]
        )

    # get human-readable description for model
    @classmethod
    def get_description(cls, model: str) -> str:
        if model in MODEL_METADATA:
            return MODEL_METADATA[model][1]
        return model

    # validate static model & return provider if valid
    @classmethod
    def validate_static(cls, model: str) -> tuple[bool, str | None]:
        resolved = cls.resolve_alias(model)
        provider = cls.get_provider(resolved)
        if provider is not None:
            return True, provider
        return False, None

    # list all models for provider (or all if provider is None)
    @classmethod
    def list_models(cls, provider: str | None = None) -> list[str]:
        if provider == "openai":
            return OPENAI_MODELS.copy()
        if provider == "anthropic":
            return CLAUDE_MODELS.copy()
        if provider is None:
            return SUPPORTED_MODELS.copy()
        return []

    # list all model aliases
    @classmethod
    def list_aliases(cls) -> dict[str, str]:
        return MODEL_ALIASES.copy()
