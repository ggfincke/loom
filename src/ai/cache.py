# src/ai/cache.py
# Unified AI cache module for provider status & response caching w/ TTL & LRU eviction

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .types import GenerateResult


# in-memory provider availability cache (static class)
class AICache:
    _provider_available: dict[str, bool] = {}
    _ollama_models: list[str] | None = None
    _ollama_error: str = ""

    # * Clear all caches (call when settings change to ensure coherence)
    @classmethod
    def invalidate_all(cls) -> None:
        cls._provider_available.clear()
        cls._ollama_models = None
        cls._ollama_error = ""

    # clear cache for specific provider
    @classmethod
    def invalidate_provider(cls, provider: str) -> None:
        cls._provider_available.pop(provider, None)
        if provider == "ollama":
            cls._ollama_models = None
            cls._ollama_error = ""

    # get cached provider availability status
    @classmethod
    def get_provider_available(cls, provider: str) -> bool | None:
        return cls._provider_available.get(provider)

    # set provider availability status
    @classmethod
    def set_provider_available(cls, provider: str, available: bool) -> None:
        cls._provider_available[provider] = available

    # check if provider status is cached
    @classmethod
    def is_provider_cached(cls, provider: str) -> bool:
        return provider in cls._provider_available

    # get cached Ollama model list
    @classmethod
    def get_ollama_models(cls) -> list[str] | None:
        return cls._ollama_models

    # get cached Ollama error message
    @classmethod
    def get_ollama_error(cls) -> str:
        return cls._ollama_error

    # set Ollama status & update provider availability
    @classmethod
    def set_ollama_status(cls, models: list[str] | None, error: str = "") -> None:
        cls._ollama_models = models
        cls._ollama_error = error
        # also update provider availability based on status
        cls._provider_available["ollama"] = models is not None and len(models) >= 0

    # check if Ollama status is cached
    @classmethod
    def is_ollama_cached(cls) -> bool:
        return cls._ollama_models is not None or cls._ollama_error != ""


# disk-based response cache w/ TTL & LRU eviction
class AIResponseCache:
    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_days: int = 7,
        enabled: bool = True,
        max_entries: int = 0,
        max_size_mb: int = 0,
    ):
        self._cache_dir = cache_dir or Path(".loom") / "cache"
        self._ttl_days = ttl_days
        self._enabled = enabled
        self._max_entries = max_entries  # 0 = unlimited
        self._max_size_mb = max_size_mb  # 0 = unlimited
        # runtime stats
        self._hits = 0
        self._misses = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    # generate cache key from prompt, model & temperature
    def _make_key(self, prompt: str, model: str, temperature: float) -> str:
        content = f"{prompt}|{model}|{temperature:.2f}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    # get file path for cache key
    def _get_cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    # check if cache entry is expired
    def _is_expired(self, entry: dict) -> bool:
        expires_at = entry.get("expires_at")
        if not expires_at:
            return True
        try:
            expiry = datetime.fromisoformat(expires_at)
            return datetime.now(timezone.utc) > expiry
        except (ValueError, TypeError):
            return True

    # * Get cached result for prompt, model & temperature (returns None if not found or expired)
    def get(self, prompt: str, model: str, temperature: float) -> GenerateResult | None:
        if not self._enabled:
            return None

        key = self._make_key(prompt, model, temperature)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self._misses += 1
            return None

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))

            # check expiration
            if self._is_expired(data):
                cache_path.unlink(missing_ok=True)
                self._misses += 1
                return None

            # reconstruct GenerateResult from cached data
            result_data = data.get("result", {})
            self._hits += 1
            return GenerateResult(
                success=result_data.get("success", False),
                data=result_data.get("data"),
                raw_text=result_data.get("raw_text", ""),
                json_text=result_data.get("json_text", ""),
                error=result_data.get("error", ""),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            # corrupted cache entry - remove it
            cache_path.unlink(missing_ok=True)
            self._misses += 1
            return None

    # * Store successful result in cache w/ TTL
    def set(
        self,
        prompt: str,
        model: str,
        temperature: float,
        result: GenerateResult,
    ) -> None:
        if not self._enabled:
            return

        # only cache successful responses
        if not result.success:
            return

        # ensure cache directory exists
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        key = self._make_key(prompt, model, temperature)
        cache_path = self._get_cache_path(key)

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=self._ttl_days)

        entry = {
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "model": model,
            "temperature": temperature,
            "prompt_hash": key,
            "result": asdict(result),
        }

        try:
            cache_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
            # enforce size/count limits after adding new entry
            self._enforce_limits()
        except OSError:
            # silently fail on write errors - cache is optional
            pass

    # * Clear all cache entries & return count of deleted files
    def clear(self) -> int:
        if not self._cache_dir.exists():
            return 0

        count = 0
        for cache_file in self._cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError:
                pass

        return count

    # * Clear expired cache entries & return count of deleted files
    def clear_expired(self) -> int:
        if not self._cache_dir.exists():
            return 0

        count = 0
        for cache_file in self._cache_dir.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                if self._is_expired(data):
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, OSError):
                # corrupted or unreadable - remove it
                try:
                    cache_file.unlink()
                    count += 1
                except OSError:
                    pass

        return count

    # * Get cache statistics including size, entries & hit rate
    def stats(self) -> dict:
        size = 0
        count = 0
        expired_count = 0

        if self._cache_dir.exists():
            for cache_file in self._cache_dir.glob("*.json"):
                try:
                    size += cache_file.stat().st_size
                    count += 1
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    if self._is_expired(data):
                        expired_count += 1
                except (json.JSONDecodeError, OSError):
                    expired_count += 1

        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "enabled": self._enabled,
            "cache_dir": str(self._cache_dir),
            "ttl_days": self._ttl_days,
            "max_entries": self._max_entries if self._max_entries > 0 else "unlimited",
            "max_size_mb": self._max_size_mb if self._max_size_mb > 0 else "unlimited",
            "entries": count,
            "expired_entries": expired_count,
            "size_bytes": size,
            "size_human": self._format_size(size),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }

    # format byte size as human-readable string
    def _format_size(self, size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    # get cache entries sorted by creation time (oldest first for LRU eviction)
    def _get_sorted_entries(self) -> list[tuple[Path, int]]:
        if not self._cache_dir.exists():
            return []

        entries: list[tuple[str, Path, int]] = []
        for cache_file in self._cache_dir.glob("*.json"):
            try:
                size = cache_file.stat().st_size
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                created = data.get("created_at", "")
                entries.append((created, cache_file, size))
            except (json.JSONDecodeError, OSError):
                # corrupted entries sort first (empty string) so they're evicted first
                entries.append(("", cache_file, 0))

        entries.sort(key=lambda x: x[0])
        return [(e[1], e[2]) for e in entries]

    # enforce max entries & size limits via LRU eviction (returns count of evicted entries)
    def _enforce_limits(self) -> int:
        if self._max_entries == 0 and self._max_size_mb == 0:
            return 0  # no limits configured

        entries = self._get_sorted_entries()
        evicted = 0

        # evict by entry count
        if self._max_entries > 0:
            while len(entries) > self._max_entries:
                oldest_path, _ = entries.pop(0)
                try:
                    oldest_path.unlink(missing_ok=True)
                    evicted += 1
                except OSError:
                    pass

        # evict by total size
        if self._max_size_mb > 0:
            max_bytes = self._max_size_mb * 1024 * 1024
            total_size = sum(size for _, size in entries)
            while total_size > max_bytes and entries:
                oldest_path, oldest_size = entries.pop(0)
                try:
                    oldest_path.unlink(missing_ok=True)
                    total_size -= oldest_size
                    evicted += 1
                except OSError:
                    pass

        return evicted


# global response cache instance (configured lazily from settings)
_response_cache: AIResponseCache | None = None
# original enabled state from settings (before any overrides)
_original_enabled: bool = True
# thread-local storage for per-invocation cache disable (--no-cache flag)
_cache_disabled_local = threading.local()


# check if cache is disabled for current thread
def _is_cache_disabled() -> bool:
    return getattr(_cache_disabled_local, "disabled", False)


# * Get global response cache instance (lazily initialized from settings)
def get_response_cache() -> AIResponseCache:
    global _response_cache, _original_enabled
    if _response_cache is None:
        # ! lazy import to avoid circular dependency w/ settings_manager
        from ..config.settings import settings_manager

        settings = settings_manager.load()
        cache_dir = Path(settings.cache_dir) if hasattr(settings, "cache_dir") else None
        ttl = getattr(settings, "cache_ttl_days", 7)
        enabled = getattr(settings, "cache_enabled", True)
        max_entries = getattr(settings, "cache_max_entries", 500)
        max_size_mb = getattr(settings, "cache_max_size_mb", 100)
        _original_enabled = enabled
        _response_cache = AIResponseCache(
            cache_dir=cache_dir,
            ttl_days=ttl,
            enabled=enabled,
            max_entries=max_entries,
            max_size_mb=max_size_mb,
        )
        # auto-cleanup expired entries on first access (silent)
        _response_cache.clear_expired()

    # apply thread-local override: disable if flag set, otherwise restore original
    if _is_cache_disabled():
        _response_cache.enabled = False
    else:
        _response_cache.enabled = _original_enabled

    return _response_cache


# reset global cache instance & thread-local state
def reset_response_cache() -> None:
    global _response_cache, _original_enabled
    _response_cache = None
    _original_enabled = True
    # reset thread-local state
    _cache_disabled_local.disabled = False


# disable cache for current invocation (thread-local, used by --no-cache flag)
def disable_cache_for_invocation() -> None:
    _cache_disabled_local.disabled = True
