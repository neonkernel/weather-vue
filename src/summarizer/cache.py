"""
Persistent disk cache for article summaries using diskcache.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False

from .models import Summary

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "summarizer"
DEFAULT_TTL_HOURS = 7 * 24  # 7 days


def _get_ttl_seconds() -> int:
    """Read TTL from environment variable, defaulting to 7 days."""
    hours = float(os.environ.get("CACHE_TTL_HOURS", DEFAULT_TTL_HOURS))
    return int(hours * 3600)


def _make_cache_key(url: str, style: str, provider: str, model: str) -> str:
    """
    Generate a SHA-256 cache key from the normalized URL, style, provider, and model.
    URL is normalized by stripping trailing slashes and lowercasing the scheme/host.
    """
    normalized = url.strip().rstrip("/").lower()
    raw = f"{normalized}|{style}|{provider}|{model}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SummaryCache:
    """
    Wraps diskcache.Cache to provide persistent Summary caching with TTL support.
    Falls back to a no-op in-memory dict when diskcache is not installed.
    """

    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: Optional[int] = None):
        self._ttl = ttl_seconds if ttl_seconds is not None else _get_ttl_seconds()
        self._dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self._cache: Optional[diskcache.Cache] = None  # type: ignore[name-defined]
        self._memory_fallback: dict[str, str] = {}

        if DISKCACHE_AVAILABLE:
            try:
                self._dir.mkdir(parents=True, exist_ok=True)
                self._cache = diskcache.Cache(str(self._dir))
                logger.debug("Disk cache initialised at %s (TTL=%ds)", self._dir, self._ttl)
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to initialise disk cache: %s — using in-memory fallback", exc)
        else:
            logger.warning(
                "diskcache not installed; caching disabled. "
                "Install it with: pip install diskcache"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def make_key(self, url: str, style: str, provider: str, model: str) -> str:
        """Return the cache key for the given parameters."""
        return _make_cache_key(url, style, provider, model)

    def get(self, key: str) -> Optional[Summary]:
        """Return a cached Summary or None on cache miss / error."""
        try:
            if self._cache is not None:
                raw = self._cache.get(key)
            else:
                raw = self._memory_fallback.get(key)

            if raw is None:
                return None

            data = json.loads(raw)
            summary = Summary(**data)
            logger.debug("Cache HIT for key %s…", key[:12])
            return summary
        except Exception as exc:
            logger.warning("Cache read error (key=%s…): %s", key[:12], exc)
            return None

    def set(self, key: str, summary: Summary) -> None:
        """Persist a Summary object under the given key with the configured TTL."""
        try:
            raw = json.dumps(summary.__dict__)
            if self._cache is not None:
                self._cache.set(key, raw, expire=self._ttl)
            else:
                self._memory_fallback[key] = raw
            logger.debug("Cache SET for key %s… (TTL=%ds)", key[:12], self._ttl)
        except Exception as exc:
            logger.warning("Cache write error (key=%s…): %s", key[:12], exc)

    def clear(self) -> int:
        """
        Delete all entries from the cache.
        Returns the number of entries deleted.
        """
        try:
            if self._cache is not None:
                count = len(self._cache)
                self._cache.clear()
                logger.info("Cleared %d entries from disk cache at %s", count, self._dir)
                return count
            else:
                count = len(self._memory_fallback)
                self._memory_fallback.clear()
                return count
        except Exception as exc:  # pragma: no cover
            logger.warning("Cache clear error: %s", exc)
            return 0

    def close(self) -> None:
        """Close the underlying diskcache handle."""
        if self._cache is not None:
            try:
                self._cache.close()
            except Exception:  # pragma: no cover
                pass

    def __len__(self) -> int:
        if self._cache is not None:
            return len(self._cache)
        return len(self._memory_fallback)

    def __enter__(self) -> "SummaryCache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()