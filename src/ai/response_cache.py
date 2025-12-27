# src/ai/response_cache.py
# Persistent disk cache for AI responses to reduce API costs
#
# * Caches successful AI responses keyed by hash of (prompt + model + temperature)
# * Supports TTL-based expiration & manual invalidation
# * Stores entries as JSON files in configurable cache directory

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .types import GenerateResult


# * Response cache for AI API calls w/ disk persistence & TTL expiration
class ResponseCache:

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_days: int = 7,
        enabled: bool = True,
    ):
        self._cache_dir = cache_dir or Path(".loom") / "cache"
        self._ttl_days = ttl_days
        self._enabled = enabled
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

    # * Generate cache key from prompt, model, & temperature
    def _make_key(self, prompt: str, model: str, temperature: float) -> str:
        # combine inputs into deterministic hash
        content = f"{prompt}|{model}|{temperature:.2f}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    # * Get cache file path for a given key
    def _get_cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    # * Check if cache entry is expired
    def _is_expired(self, entry: dict) -> bool:
        expires_at = entry.get("expires_at")
        if not expires_at:
            return True
        try:
            expiry = datetime.fromisoformat(expires_at)
            return datetime.now(timezone.utc) > expiry
        except (ValueError, TypeError):
            return True

    # * Retrieve cached response if exists & not expired
    def get(
        self, prompt: str, model: str, temperature: float
    ) -> Optional[GenerateResult]:
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

    # * Store successful response in cache
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
        except OSError:
            # silently fail on write errors - cache is optional
            pass

    # * Clear all cached entries, returns count of removed files
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

    # * Clear only expired entries, returns count of removed files
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

    # * Get cache statistics
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
            "entries": count,
            "expired_entries": expired_count,
            "size_bytes": size,
            "size_human": self._format_size(size),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }

    # * Format bytes as human-readable size
    def _format_size(self, size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# * Global response cache instance (configured lazily from settings)
_response_cache: Optional[ResponseCache] = None
# * Temporary override for --no-cache flag (thread-local would be better for concurrency)
_cache_disabled_override: bool = False


# * Get or create the global response cache instance
def get_response_cache() -> ResponseCache:
    global _response_cache
    if _response_cache is None:
        # lazy import to avoid circular dependency
        from ..config.settings import settings_manager

        settings = settings_manager.load()
        cache_dir = Path(settings.cache_dir) if hasattr(settings, "cache_dir") else None
        ttl = getattr(settings, "cache_ttl_days", 7)
        enabled = getattr(settings, "cache_enabled", True)
        _response_cache = ResponseCache(
            cache_dir=cache_dir,
            ttl_days=ttl,
            enabled=enabled,
        )

    # apply temporary override if set
    if _cache_disabled_override:
        _response_cache.enabled = False

    return _response_cache


# * Reset the global cache instance (for testing or settings changes)
def reset_response_cache() -> None:
    global _response_cache, _cache_disabled_override
    _response_cache = None
    _cache_disabled_override = False


# * Temporarily disable cache for current invocation (--no-cache flag)
def disable_cache_for_invocation() -> None:
    global _cache_disabled_override
    _cache_disabled_override = True
