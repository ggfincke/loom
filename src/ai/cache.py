# src/ai/cache.py
# Unified AI cache for provider status & Ollama model list
#
# * This cache is AI-only. Settings cache remains in SettingsManager.
# * Call invalidate_all() when settings change to ensure coherence.

from typing import Optional


# centralized cache for AI provider availability & Ollama models
# cache keys use canonical provider IDs: "openai", "anthropic", "ollama"
class AICache:

    _provider_available: dict[str, bool] = {}
    _ollama_models: Optional[list[str]] = None
    _ollama_error: str = ""

    @classmethod
    # coordinated cache invalidation - called when settings change
    def invalidate_all(cls) -> None:
        cls._provider_available.clear()
        cls._ollama_models = None
        cls._ollama_error = ""

    @classmethod
    # invalidate cache for a specific provider
    def invalidate_provider(cls, provider: str) -> None:
        cls._provider_available.pop(provider, None)
        if provider == "ollama":
            cls._ollama_models = None
            cls._ollama_error = ""

    # * Provider availability caching

    @classmethod
    # get cached availability status for a provider (None if not cached, bool if cached)
    def get_provider_available(cls, provider: str) -> Optional[bool]:
        return cls._provider_available.get(provider)

    @classmethod
    # cache availability status for a provider
    def set_provider_available(cls, provider: str, available: bool) -> None:
        cls._provider_available[provider] = available

    @classmethod
    # check if provider status is cached
    def is_provider_cached(cls, provider: str) -> bool:
        return provider in cls._provider_available

    # * Ollama-specific caching

    @classmethod
    # get cached Ollama models (returns None if not cached)
    def get_ollama_models(cls) -> Optional[list[str]]:
        return cls._ollama_models

    @classmethod
    # get cached Ollama error message (empty string if no error)
    def get_ollama_error(cls) -> str:
        return cls._ollama_error

    @classmethod
    # cache Ollama status (models list & error message)
    def set_ollama_status(cls, models: Optional[list[str]], error: str = "") -> None:
        cls._ollama_models = models
        cls._ollama_error = error
        # also update provider availability based on status
        cls._provider_available["ollama"] = models is not None and len(models) >= 0

    @classmethod
    # check if Ollama status is cached
    def is_ollama_cached(cls) -> bool:
        return cls._ollama_models is not None or cls._ollama_error != ""
