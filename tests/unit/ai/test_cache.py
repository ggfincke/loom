# tests/unit/ai/test_cache.py
# Unit tests for AICache

import pytest
from src.ai.cache import AICache


class TestAICache:
    # Test AICache functionality.

    def setup_method(self):
        # Reset cache before each test.
        AICache.invalidate_all()

    def teardown_method(self):
        # Clean up after each test.
        AICache.invalidate_all()


class TestProviderAvailability(TestAICache):
    # Test provider availability caching.

    # * Verify get provider available returns none when not cached
    def test_get_provider_available_returns_none_when_not_cached(self):
        assert AICache.get_provider_available("openai") is None
        assert AICache.get_provider_available("anthropic") is None
        assert AICache.get_provider_available("ollama") is None

    # * Verify set & get provider available
    def test_set_and_get_provider_available(self):
        AICache.set_provider_available("openai", True)
        assert AICache.get_provider_available("openai") is True

        AICache.set_provider_available("anthropic", False)
        assert AICache.get_provider_available("anthropic") is False

    # * Verify is provider cached
    def test_is_provider_cached(self):
        assert AICache.is_provider_cached("openai") is False

        AICache.set_provider_available("openai", True)
        assert AICache.is_provider_cached("openai") is True

    # * Verify invalidate provider clears specific provider
    def test_invalidate_provider_clears_specific_provider(self):
        AICache.set_provider_available("openai", True)
        AICache.set_provider_available("anthropic", True)

        AICache.invalidate_provider("openai")

        assert AICache.get_provider_available("openai") is None
        assert AICache.get_provider_available("anthropic") is True

    # * Verify invalidate all clears all providers
    def test_invalidate_all_clears_all_providers(self):
        AICache.set_provider_available("openai", True)
        AICache.set_provider_available("anthropic", True)

        AICache.invalidate_all()

        assert AICache.get_provider_available("openai") is None
        assert AICache.get_provider_available("anthropic") is None


class TestOllamaStatus(TestAICache):
    # Test Ollama-specific caching.

    # * Verify get ollama models returns none when not cached
    def test_get_ollama_models_returns_none_when_not_cached(self):
        assert AICache.get_ollama_models() is None

    # * Verify get ollama error returns empty when not cached
    def test_get_ollama_error_returns_empty_when_not_cached(self):
        assert AICache.get_ollama_error() == ""

    # * Verify set ollama status w/ models
    def test_set_ollama_status_with_models(self):
        models = ["llama3.2", "mistral"]
        AICache.set_ollama_status(models)

        assert AICache.get_ollama_models() == models
        assert AICache.get_ollama_error() == ""
        assert AICache.get_provider_available("ollama") is True

    # * Verify set ollama status w/ error
    def test_set_ollama_status_with_error(self):
        AICache.set_ollama_status(None, "Connection failed")

        assert AICache.get_ollama_models() is None
        assert AICache.get_ollama_error() == "Connection failed"

    # * Verify is ollama cached w/ models
    def test_is_ollama_cached_with_models(self):
        assert AICache.is_ollama_cached() is False

        AICache.set_ollama_status(["llama3.2"])
        assert AICache.is_ollama_cached() is True

    # * Verify is ollama cached w/ error
    def test_is_ollama_cached_with_error(self):
        AICache.set_ollama_status(None, "Error")
        assert AICache.is_ollama_cached() is True

    # * Verify invalidate provider ollama clears ollama cache
    def test_invalidate_provider_ollama_clears_ollama_cache(self):
        AICache.set_ollama_status(["llama3.2"], "")

        AICache.invalidate_provider("ollama")

        assert AICache.get_ollama_models() is None
        assert AICache.get_ollama_error() == ""

    # * Verify invalidate all clears ollama cache
    def test_invalidate_all_clears_ollama_cache(self):
        AICache.set_ollama_status(["llama3.2"], "")
        AICache.set_provider_available("openai", True)

        AICache.invalidate_all()

        assert AICache.get_ollama_models() is None
        assert AICache.get_ollama_error() == ""
        assert AICache.get_provider_available("openai") is None


class TestCacheCoordination(TestAICache):
    # Test coordinated cache invalidation.

    # * Verify set ollama status updates provider available
    def test_set_ollama_status_updates_provider_available(self):
        # Setting models should mark provider as available
        AICache.set_ollama_status(["llama3.2"])
        assert AICache.get_provider_available("ollama") is True

        # Empty models list should still mark as available (server running)
        AICache.invalidate_all()
        AICache.set_ollama_status([])
        assert AICache.get_provider_available("ollama") is True
