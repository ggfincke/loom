# src/ai/cache.py
# Unified AI cache for provider status & Ollama model list
#
# * This cache is AI-only. Settings cache remains in SettingsManager.
# * Call invalidate_all() when settings change to ensure coherence.

from typing import Optional


class AICache:
    """Centralized cache for AI provider availability & Ollama models.

    Cache keys use canonical provider IDs: "openai", "anthropic", "ollama".
    """

    _provider_available: dict[str, bool] = {}
    _ollama_models: Optional[list[str]] = None
    _ollama_error: str = ""

    @classmethod
    def invalidate_all(cls) -> None:
        """Coordinated cache invalidation - called when settings change."""
        cls._provider_available.clear()
        cls._ollama_models = None
        cls._ollama_error = ""

    @classmethod
    def invalidate_provider(cls, provider: str) -> None:
        """Invalidate cache for a specific provider."""
        cls._provider_available.pop(provider, None)
        if provider == "ollama":
            cls._ollama_models = None
            cls._ollama_error = ""

    # * Provider availability caching

    @classmethod
    def get_provider_available(cls, provider: str) -> Optional[bool]:
        """Get cached availability status for a provider.

        Returns None if not cached, bool if cached.
        """
        return cls._provider_available.get(provider)

    @classmethod
    def set_provider_available(cls, provider: str, available: bool) -> None:
        """Cache availability status for a provider."""
        cls._provider_available[provider] = available

    @classmethod
    def is_provider_cached(cls, provider: str) -> bool:
        """Check if provider status is cached."""
        return provider in cls._provider_available

    # * Ollama-specific caching

    @classmethod
    def get_ollama_models(cls) -> Optional[list[str]]:
        """Get cached Ollama models. Returns None if not cached."""
        return cls._ollama_models

    @classmethod
    def get_ollama_error(cls) -> str:
        """Get cached Ollama error message. Empty string if no error."""
        return cls._ollama_error

    @classmethod
    def set_ollama_status(
        cls, models: Optional[list[str]], error: str = ""
    ) -> None:
        """Cache Ollama status (models list & error message)."""
        cls._ollama_models = models
        cls._ollama_error = error
        # also update provider availability based on status
        cls._provider_available["ollama"] = models is not None and len(models) >= 0

    @classmethod
    def is_ollama_cached(cls) -> bool:
        """Check if Ollama status is cached."""
        return cls._ollama_models is not None or cls._ollama_error != ""
