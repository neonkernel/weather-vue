"""
Persistent disk cache for summaries using diskcache.
"""

import hashlib
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False

from summarizer.models import Summary

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "summarizer"
DEFAULT_TTL_HOURS = 7 * 24  # 7 days in hours


def _get_ttl_seconds() -> int:
    """Get cache TTL in seconds from environment variable or default."""
    ttl_hours = float(os.environ.get("CACHE_TTL_HOURS", DEFAULT_TTL_HOURS))
    return int(ttl_hours * 3600)


def _make_cache_key(url: str, style: str, provider: str, model: str) -> str:
    """
    Generate a SHA-256 cache key from the combination of URL, style, provider, and model.
    URL is normalized (lowercased, stripped, fragment removed).
    """
    # Normalize URL
    normalized_url = url.strip().lower()
    # Remove fragment
    if "#" in normalized_url:
        normalized_url = normalized_url.split("#")[0]
    # Remove trailing slash for consistency
    normalized_url = normalized_url.rstrip("/")

    key_material = f"{normalized_url}|{style.strip().lower()}|{provider.strip().lower()}|{model.strip().lower()}"
    return hashlib.sha256(key_material.encode("utf-8")).hexdigest()


class SummaryCache:
    """
    A persistent disk cache for Summary objects.
    Uses diskcache under the hood for safe concurrent access and TTL support.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_seconds: Optional[int] = None,
        enabled: bool = True,
    ):
        self.enabled = enabled and DISKCACHE_AVAILABLE
        self._cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self._ttl = ttl_seconds if ttl_seconds is not None else _get_ttl_seconds()
        self._cache: Optional["diskcache.Cache"] = None

        if enabled and not DISKCACHE_AVAILABLE:
            logger.warning(
                "diskcache is not installed. Caching will be disabled. "
                "Install it with: pip install diskcache"
            )

        if self.enabled:
            self._open()

    def _open(self) -> None:
        """Open (or create) the diskcache Cache."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache = diskcache.Cache(str(self._cache_dir))
            logger.debug("Cache opened at %s (TTL=%ds)", self._cache_dir, self._ttl)
        except Exception as exc:
            logger.error("Failed to open cache at %s: %s", self._cache_dir, exc)
            self.enabled = False
            self._cache = None

    def _serialize(self, summary: Summary) -> str:
        """Serialize a Summary to JSON string."""
        data = asdict(summary)
        return json.dumps(data, default=str)

    def _deserialize(self, raw: str) -> Summary:
        """Deserialize a JSON string back to a Summary."""
        data = json.loads(raw)
        return Summary(**data)

    def get(self, url: str, style: str, provider: str, model: str) -> Optional[Summary]:
        """
        Look up a cached Summary. Returns None on miss or if cache is disabled.
        """
        if not self.enabled or self._cache is None:
            return None

        key = _make_cache_key(url, style, provider, model)
        try:
            raw = self._cache.get(key)
            if raw is None:
                logger.debug("Cache miss for key %s", key[:12])
                return None
            summary = self._deserialize(raw)
            logger.debug("Cache hit for key %s", key[:12])
            return summary
        except Exception as exc:
            logger.warning("Cache read error for key %s: %s", key[:12], exc)
            return None

    def set(self, url: str, style: str, provider: str, model: str, summary: Summary) -> bool:
        """
        Store a Summary in the cache. Returns True on success.
        """
        if not self.enabled or self._cache is None:
            return False

        key = _make_cache_key(url, style, provider, model)
        try:
            raw = self._serialize(summary)
            self._cache.set(key, raw, expire=self._ttl)
            logger.debug("Cached summary for key %s (TTL=%ds)", key[:12], self._ttl)
            return True
        except Exception as exc:
            logger.warning("Cache write error for key %s: %s", key[:12], exc)
            return False

    def clear(self) -> int:
        """
        Clear all entries from the cache. Returns the number of entries removed.
        """
        if not self.enabled or self._cache is None:
            return 0

        try:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Cache cleared (%d entries removed)", count)
            return count
        except Exception as exc:
            logger.error("Cache clear error: %s", exc)
            return 0

    def close(self) -> None:
        """Close the underlying cache (flush to disk)."""
        if self._cache is not None:
            try:
                self._cache.close()
            except Exception as exc:
                logger.warning("Cache close error: %s", exc)

    def __enter__(self) -> "SummaryCache":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @property
    def size(self) -> int:
        """Return number of entries currently in the cache."""
        if not self.enabled or self._cache is None:
            return 0
        try:
            return len(self._cache)
        except Exception:
            return 0

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir