"""Persistent disk cache for summaries using diskcache."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from .models import Summary

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "summarizer"
DEFAULT_TTL_HOURS = 7 * 24  # 7 days


def _get_ttl_seconds() -> int:
    """Return cache TTL in seconds from env var or default."""
    hours = float(os.environ.get("CACHE_TTL_HOURS", DEFAULT_TTL_HOURS))
    return int(hours * 3600)


def _make_cache_key(url: str, style: str, provider: str, model: str) -> str:
    """Generate a SHA-256 cache key from the normalized inputs."""
    normalized_url = url.strip().lower()
    raw = f"{normalized_url}|{style}|{provider}|{model}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SummaryCache:
    """Persistent cache for Summary objects backed by diskcache."""

    def __init__(self, cache_dir: Optional[Path] = None, enabled: bool = True):
        self._enabled = enabled
        self._cache = None

        if not enabled:
            logger.debug("Cache disabled.")
            return

        try:
            import diskcache  # type: ignore

            cache_path = cache_dir or Path(
                os.environ.get("SUMMARIZER_CACHE_DIR", str(DEFAULT_CACHE_DIR))
            )
            cache_path.mkdir(parents=True, exist_ok=True)
            self._cache = diskcache.Cache(str(cache_path))
            logger.debug("Cache initialized at %s", cache_path)
        except ImportError:
            logger.warning(
                "diskcache not installed; caching disabled. "
                "Install it with: pip install diskcache"
            )
            self._enabled = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, url: str, style: str, provider: str, model: str) -> Optional[Summary]:
        """Return a cached Summary or None if not found / expired."""
        if not self._enabled or self._cache is None:
            return None

        key = _make_cache_key(url, style, provider, model)
        try:
            raw = self._cache.get(key)
            if raw is None:
                logger.debug("Cache miss for key %s", key[:12])
                return None

            summary = Summary(**json.loads(raw))
            logger.debug("Cache hit for key %s", key[:12])
            return summary
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache read error: %s", exc)
            return None

    def set(
        self,
        url: str,
        style: str,
        provider: str,
        model: str,
        summary: Summary,
    ) -> None:
        """Store a Summary in the cache with the configured TTL."""
        if not self._enabled or self._cache is None:
            return

        key = _make_cache_key(url, style, provider, model)
        ttl = _get_ttl_seconds()
        try:
            payload = json.dumps(
                {
                    "url": summary.url,
                    "title": summary.title,
                    "summary": summary.summary,
                    "style": summary.style,
                    "provider": summary.provider,
                    "model": summary.model,
                    "word_count": summary.word_count,
                    "chunk_count": summary.chunk_count,
                    "elapsed_seconds": summary.elapsed_seconds,
                }
            )
            self._cache.set(key, payload, expire=ttl)
            logger.debug("Cached summary under key %s (TTL %ds)", key[:12], ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache write error: %s", exc)

    def clear(self) -> int:
        """Clear all entries. Returns number of items removed."""
        if self._cache is None:
            return 0
        count = len(self._cache)
        self._cache.clear()
        logger.info("Cache cleared (%d entries removed).", count)
        return count

    def close(self) -> None:
        """Close the underlying cache connection."""
        if self._cache is not None:
            self._cache.close()

    def __enter__(self) -> "SummaryCache":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()