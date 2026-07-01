"""
Tests for SummaryCache: hit/miss behavior, TTL expiration, and cache key collision resistance.
"""

import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from unittest.mock import patch

import pytest

from summarizer.cache import SummaryCache, _make_cache_key


# ---------------------------------------------------------------------------
# Minimal Summary stand-in for tests that don't need the full models module
# ---------------------------------------------------------------------------


@dataclass
class _Summary:
    url: str
    title: str
    text: str
    style: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    cached: bool = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache(tmp_path):
    """A SummaryCache backed by a temporary directory."""
    c = SummaryCache(cache_dir=tmp_path / "cache", ttl_seconds=3600)
    yield c
    c.close()


@pytest.fixture
def sample_summary():
    return _Summary(
        url="https://example.com/article",
        title="Test Article",
        text="This is a summary.",
        style="concise",
        provider="openai",
        model="gpt-4o-mini",
        tokens_used=120,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make(url, style="concise", provider="openai", model="gpt-4o-mini", text="Summary."):
    return _Summary(
        url=url, title="T", text=text, style=style, provider=provider, model=model
    )


# ---------------------------------------------------------------------------
# Cache key generation
# ---------------------------------------------------------------------------


class TestCacheKeyGeneration:
    def test_key_is_64_hex_chars(self):
        key = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_same_inputs_produce_same_key(self):
        k1 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o")
        k2 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o")
        assert k1 == k2

    def test_different_style_produces_different_key(self):
        k1 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o")
        k2 = _make_cache_key("https://example.com", "detailed", "openai", "gpt-4o")
        assert k1 != k2

    def test_different_provider_produces_different_key(self):
        k1 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o")
        k2 = _make_cache_key("https://example.com", "concise", "anthropic", "gpt-4o")
        assert k1 != k2

    def test_different_model_produces_different_key(self):
        k1 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o")
        k2 = _make_cache_key("https://example.com", "concise", "openai", "gpt-3.5-turbo")
        assert k1 != k2

    def test_url_normalization_strips_fragment(self):
        k1 = _make_cache_key("https://example.com/page", "concise", "openai", "gpt-4o")
        k2 = _make_cache_key("https://example.com/page#section", "concise", "openai", "gpt-4o")
        assert k1 == k2

    def test_url_normalization_strips_trailing_slash(self):
        k1 = _make_cache_key("https://example.com/page", "concise", "openai", "gpt-4o")
        k2 = _make_cache_key("https://example.com/page/", "concise", "openai", "gpt-4o")
        assert k1 == k2

    def test_url_normalization_is_case_insensitive(self):
        k1 = _make_cache_key("https://EXAMPLE.COM/page", "concise", "openai", "gpt-4o")
        k2 = _make_cache_key("https://example.com/page", "concise", "openai", "gpt-4o")
        assert k1 == k2

    def test_collision_resistance(self):
        """Many different URLs should all produce unique keys."""
        urls = [f"https://example.com/article-{i}" for i in range(100)]
        keys = {_make_cache_key(u, "concise", "openai", "gpt-4o") for u in urls}
        assert len(keys) == 100


# ---------------------------------------------------------------------------
# Cache miss behavior
# ---------------------------------------------------------------------------


class TestCacheMiss:
    def test_get_returns_none_on_empty_cache(self, cache, sample_summary):
        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is None

    def test_get_returns_none_for_unknown_url(self, cache, sample_summary):
        cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        result = cache.get(
            url="https://totally-different.com",
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is None

    def test_get_returns_none_for_different_style(self, cache, sample_summary):
        cache.set(
            url=sample_summary.url,
            style="concise",
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        result = cache.get(
            url=sample_summary.url,
            style="detailed",
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is None

    def test_get_returns_none_for_different_provider(self, cache, sample_summary):
        cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider="openai",
            model=sample_summary.model,
            summary=sample_summary,
        )
        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider="anthropic",
            model=sample_summary.model,
        )
        assert result is None


# ---------------------------------------------------------------------------
# Cache hit behavior
# ---------------------------------------------------------------------------


class TestCacheHit:
    def test_set_and_get_returns_summary(self, cache, sample_summary):
        cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is not None
        assert result.text == sample_summary.text
        assert result.title == sample_summary.title

    def test_cache_persists_all_fields(self, cache):
        summary = _Summary(
            url="https://example.com/full",
            title="Full Article",
            text="Detailed summary here.",
            style="detailed",
            provider="anthropic",
            model="claude-3-haiku",
            tokens_used=500,
            cached=False,
        )
        cache.set(
            url=summary.url,
            style=summary.style,
            provider=summary.provider,
            model=summary.model,
            summary=summary,
        )
        result = cache.get(
            url=summary.url,
            style=summary.style,
            provider=summary.provider,
            model=summary.model,
        )
        assert result.url == summary.url
        assert result.title == summary.title
        assert result.text == summary.text
        assert result.style == summary.style
        assert result.provider == summary.provider
        assert result.model == summary.model
        assert result.tokens_used == summary.tokens_used

    def test_url_with_fragment_hits_cache(self, cache, sample_summary):
        cache.set(
            url="https://example.com/article",
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        # Same URL with fragment should be a hit
        result = cache.get(
            url="https://example.com/article#introduction",
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is not None

    def test_url_with_trailing_slash_hits_cache(self, cache, sample_summary):
        cache.set(
            url="https://example.com/article",
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        result = cache.get(
            url="https://example.com/article/",
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is not None

    def test_set_returns_true_on_success(self, cache, sample_summary):
        result = cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        assert result is True

    def test_overwrite_updates_cached_value(self, cache, sample_summary):
        cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        updated = _Summary(
            url=sample_summary.url,
            title="Updated Title",
            text="Updated summary text.",
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        cache.set(
            url=updated.url,
            style=updated.style,
            provider=updated.provider,
            model=updated.model,
            summary=updated,
        )
        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result.text == "Updated summary text."
        assert result.title == "Updated Title"


# ---------------------------------------------------------------------------
# TTL expiration
# ---------------------------------------------------------------------------


class TestTTLExpiration:
    def test_entry_is_expired_after_ttl(self, tmp_path, sample_summary):
        """Use a 1-second TTL and wait for expiry."""
        cache = SummaryCache(cache_dir=tmp_path / "cache", ttl_seconds=1)
        cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        # Should be present immediately
        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is not None

        # Wait for TTL to expire
        time.sleep(1.5)

        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is None
        cache.close()

    def test_entry_not_expired_within_ttl(self, tmp_path, sample_summary):
        """Entry should still be present well within TTL."""
        cache = SummaryCache(cache_dir=tmp_path / "cache", ttl_seconds=60)
        cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        time.sleep(0.1)
        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is not None
        cache.close()


# ---------------------------------------------------------------------------
# Cache clear / size
# ---------------------------------------------------------------------------


class TestCacheClearAndSize:
    def test_size_increases_after_set(self, cache, sample_summary):
        assert cache.size == 0
        cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        assert cache.size == 1

    def test_clear_removes_all_entries(self, cache):
        for i in range(5):
            s = _make(f"https://example.com/article-{i}")
            cache.set(url=s.url, style=s.style, provider=s.provider, model=s.model, summary=s)
        assert cache.size == 5
        removed = cache.clear()
        assert removed == 5
        assert cache.size == 0

    def test_clear_returns_zero_on_empty_cache(self, cache):
        assert cache.clear() == 0

    def test_get_returns_none_after_clear(self, cache, sample_summary):
        cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        cache.clear()
        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is None


# ---------------------------------------------------------------------------
# Disabled cache
# ---------------------------------------------------------------------------


class TestDisabledCache:
    def test_disabled_cache_get_returns_none(self, tmp_path, sample_summary):
        cache = SummaryCache(cache_dir=tmp_path / "cache", enabled=False)
        result = cache.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is None

    def test_disabled_cache_set_returns_false(self, tmp_path, sample_summary):
        cache = SummaryCache(cache_dir=tmp_path / "cache", enabled=False)
        result = cache.set(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
            summary=sample_summary,
        )
        assert result is False

    def test_disabled_cache_clear_returns_zero(self, tmp_path):
        cache = SummaryCache(cache_dir=tmp_path / "cache", enabled=False)
        assert cache.clear() == 0

    def test_disabled_cache_size_is_zero(self, tmp_path):
        cache = SummaryCache(cache_dir=tmp_path / "cache", enabled=False)
        assert cache.size == 0


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestCacheContextManager:
    def test_context_manager_closes_cache(self, tmp_path, sample_summary):
        with SummaryCache(cache_dir=tmp_path / "cache") as cache:
            cache.set(
                url=sample_summary.url,
                style=sample_summary.style,
                provider=sample_summary.provider,
                model=sample_summary.model,
                summary=sample_summary,
            )
        # Cache should be closed but data persisted
        cache2 = SummaryCache(cache_dir=tmp_path / "cache")
        result = cache2.get(
            url=sample_summary.url,
            style=sample_summary.style,
            provider=sample_summary.provider,
            model=sample_summary.model,
        )
        assert result is not None
        cache2.close()


# ---------------------------------------------------------------------------
# TTL from environment variable
# ---------------------------------------------------------------------------


class TestTTLFromEnv:
    def test_ttl_from_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CACHE_TTL_HOURS", "48")
        from summarizer.cache import _get_ttl_seconds
        ttl = _get_ttl_seconds()
        assert ttl == 48 * 3600

    def test_default_ttl(self, monkeypatch):
        monkeypatch.delenv("CACHE_TTL_HOURS", raising=False)
        from summarizer.cache import _get_ttl_seconds, DEFAULT_TTL_HOURS
        ttl = _get_ttl_seconds()
        assert ttl == int(DEFAULT_TTL_HOURS * 3600)