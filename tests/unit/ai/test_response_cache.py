# tests/unit/ai/test_response_cache.py
# Unit tests for ResponseCache

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.ai.response_cache import (
    ResponseCache,
    get_response_cache,
    reset_response_cache,
    disable_cache_for_invocation,
)
from src.ai.types import GenerateResult


class TestResponseCache:
    # Test ResponseCache functionality.

    @pytest.fixture
    def temp_cache_dir(self):
        # Create temporary directory for cache tests.
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cache(self, temp_cache_dir):
        # Create fresh cache instance for testing.
        return ResponseCache(cache_dir=temp_cache_dir, ttl_days=7, enabled=True)

    @pytest.fixture
    def sample_result(self):
        # Sample successful GenerateResult for testing.
        return GenerateResult(
            success=True,
            data={"ops": [{"op": "replace_line", "l": 1, "t": "test"}]},
            raw_text='{"ops": []}',
            json_text='{"ops": []}',
            error="",
        )


class TestCacheBasicOperations(TestResponseCache):
    # Test basic cache get/set operations.

    # * Verify cache miss returns none
    def test_cache_miss_returns_none(self, cache):
        result = cache.get("test prompt", "gpt-4", 0.2)
        assert result is None

    # * Verify cache set & get
    def test_cache_set_and_get(self, cache, sample_result):
        prompt = "Test prompt"
        model = "gpt-4"
        temp = 0.2

        cache.set(prompt, model, temp, sample_result)
        cached = cache.get(prompt, model, temp)

        assert cached is not None
        assert cached.success is True
        assert cached.data == sample_result.data

    # * Verify cache miss different prompt
    def test_cache_miss_different_prompt(self, cache, sample_result):
        cache.set("prompt1", "gpt-4", 0.2, sample_result)

        cached = cache.get("prompt2", "gpt-4", 0.2)
        assert cached is None

    # * Verify cache miss different model
    def test_cache_miss_different_model(self, cache, sample_result):
        cache.set("prompt", "gpt-4", 0.2, sample_result)

        cached = cache.get("prompt", "gpt-3.5-turbo", 0.2)
        assert cached is None

    # * Verify cache miss different temperature
    def test_cache_miss_different_temperature(self, cache, sample_result):
        cache.set("prompt", "gpt-4", 0.2, sample_result)

        cached = cache.get("prompt", "gpt-4", 0.5)
        assert cached is None

    # * Verify cache does not store failures
    def test_cache_does_not_store_failures(self, cache):
        failure = GenerateResult(success=False, error="API error")

        cache.set("prompt", "gpt-4", 0.2, failure)
        cached = cache.get("prompt", "gpt-4", 0.2)

        assert cached is None


class TestCacheDisabled(TestResponseCache):
    # Test cache behavior when disabled.

    # * Verify disabled cache does not store
    def test_disabled_cache_does_not_store(self, temp_cache_dir, sample_result):
        cache = ResponseCache(cache_dir=temp_cache_dir, enabled=False)

        cache.set("prompt", "gpt-4", 0.2, sample_result)
        cached = cache.get("prompt", "gpt-4", 0.2)

        assert cached is None

    # * Verify can toggle enabled
    def test_can_toggle_enabled(self, cache, sample_result):
        cache.set("prompt", "gpt-4", 0.2, sample_result)
        assert cache.get("prompt", "gpt-4", 0.2) is not None

        cache.enabled = False
        assert cache.get("prompt", "gpt-4", 0.2) is None

        cache.enabled = True
        assert cache.get("prompt", "gpt-4", 0.2) is not None


class TestCacheExpiration(TestResponseCache):
    # Test TTL & expiration.

    # * Verify expired entry returns none
    def test_expired_entry_returns_none(self, temp_cache_dir, sample_result):
        # create cache w/ very short TTL
        cache = ResponseCache(cache_dir=temp_cache_dir, ttl_days=0)

        cache.set("prompt", "gpt-4", 0.2, sample_result)

        # manually expire the entry
        cache_files = list(temp_cache_dir.glob("*.json"))
        assert len(cache_files) == 1

        # modify expiration to be in the past
        data = json.loads(cache_files[0].read_text())
        data["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).isoformat()
        cache_files[0].write_text(json.dumps(data))

        # should return None for expired entry
        cached = cache.get("prompt", "gpt-4", 0.2)
        assert cached is None

    # * Verify valid entry not expired
    def test_valid_entry_not_expired(self, cache, sample_result):
        cache.set("prompt", "gpt-4", 0.2, sample_result)

        cached = cache.get("prompt", "gpt-4", 0.2)
        assert cached is not None


class TestCacheClear(TestResponseCache):
    # Test cache clearing functionality.

    # * Verify clear removes all entries
    def test_clear_removes_all_entries(self, cache, sample_result):
        cache.set("prompt1", "gpt-4", 0.2, sample_result)
        cache.set("prompt2", "gpt-4", 0.2, sample_result)
        cache.set("prompt3", "gpt-4", 0.2, sample_result)

        count = cache.clear()
        assert count == 3

        assert cache.get("prompt1", "gpt-4", 0.2) is None
        assert cache.get("prompt2", "gpt-4", 0.2) is None
        assert cache.get("prompt3", "gpt-4", 0.2) is None

    # * Verify clear empty cache returns zero
    def test_clear_empty_cache_returns_zero(self, cache):
        count = cache.clear()
        assert count == 0

    # * Verify clear expired only removes expired
    def test_clear_expired_only_removes_expired(self, temp_cache_dir, sample_result):
        cache = ResponseCache(cache_dir=temp_cache_dir, ttl_days=7)

        cache.set("prompt1", "gpt-4", 0.2, sample_result)
        cache.set("prompt2", "gpt-4", 0.2, sample_result)

        # manually expire one entry
        cache_files = list(temp_cache_dir.glob("*.json"))
        data = json.loads(cache_files[0].read_text())
        data["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).isoformat()
        cache_files[0].write_text(json.dumps(data))

        count = cache.clear_expired()
        assert count == 1

        # one entry should remain
        stats = cache.stats()
        assert stats["entries"] == 1


class TestCacheStats(TestResponseCache):
    # Test cache statistics.

    # * Verify stats empty cache
    def test_stats_empty_cache(self, cache):
        stats = cache.stats()

        assert stats["enabled"] is True
        assert stats["entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == "0.0%"

    # * Verify stats w/ entries
    def test_stats_with_entries(self, cache, sample_result):
        cache.set("prompt1", "gpt-4", 0.2, sample_result)
        cache.set("prompt2", "gpt-4", 0.2, sample_result)

        stats = cache.stats()
        assert stats["entries"] == 2

    # * Verify stats tracks hits & misses
    def test_stats_tracks_hits_and_misses(self, cache, sample_result):
        cache.set("prompt", "gpt-4", 0.2, sample_result)

        # one hit
        cache.get("prompt", "gpt-4", 0.2)
        # two misses
        cache.get("other", "gpt-4", 0.2)
        cache.get("another", "gpt-4", 0.2)

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["hit_rate"] == "33.3%"


class TestGlobalCache:
    # Test global cache functions.

    def setup_method(self):
        reset_response_cache()

    def teardown_method(self):
        reset_response_cache()

    # * Verify get response cache returns singleton
    def test_get_response_cache_returns_singleton(self):
        cache1 = get_response_cache()
        cache2 = get_response_cache()
        assert cache1 is cache2

    # * Verify reset response cache clears singleton
    def test_reset_response_cache_clears_singleton(self):
        cache1 = get_response_cache()
        reset_response_cache()
        cache2 = get_response_cache()
        assert cache1 is not cache2

    # * Verify disable cache for invocation
    def test_disable_cache_for_invocation(self):
        cache = get_response_cache()
        assert cache.enabled is True

        disable_cache_for_invocation()
        cache = get_response_cache()
        assert cache.enabled is False

        # reset should clear the override
        reset_response_cache()
        cache = get_response_cache()
        assert cache.enabled is True


class TestCacheKeyGeneration(TestResponseCache):
    # Test cache key determinism.

    # * Verify same inputs same key
    def test_same_inputs_same_key(self, cache):
        key1 = cache._make_key("prompt", "gpt-4", 0.2)
        key2 = cache._make_key("prompt", "gpt-4", 0.2)
        assert key1 == key2

    # * Verify different prompt different key
    def test_different_prompt_different_key(self, cache):
        key1 = cache._make_key("prompt1", "gpt-4", 0.2)
        key2 = cache._make_key("prompt2", "gpt-4", 0.2)
        assert key1 != key2

    # * Verify different model different key
    def test_different_model_different_key(self, cache):
        key1 = cache._make_key("prompt", "gpt-4", 0.2)
        key2 = cache._make_key("prompt", "gpt-3.5-turbo", 0.2)
        assert key1 != key2

    # * Verify different temperature different key
    def test_different_temperature_different_key(self, cache):
        key1 = cache._make_key("prompt", "gpt-4", 0.2)
        key2 = cache._make_key("prompt", "gpt-4", 0.5)
        assert key1 != key2

    # * Verify key is deterministic hash
    def test_key_is_deterministic_hash(self, cache):
        key = cache._make_key("test", "gpt-4", 0.2)
        # should be 16 char hex string (first 16 chars of SHA256)
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)
