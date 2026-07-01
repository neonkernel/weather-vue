"""Tests for the SummaryCache class."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.summarizer.cache import SummaryCache, _make_cache_key
from src.summarizer.models import Summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary(**overrides) -> Summary:
    defaults = dict(
        url="https://example.com/article",
        title="Test Article",
        summary="This is a test summary.",
        style="concise",
        provider="openai",
        model="gpt-4o-mini",
        word_count=6,
        chunk_count=1,
        elapsed_seconds=1.23,
    )
    defaults.update(overrides)
    return Summary(**defaults)


# ---------------------------------------------------------------------------
# Cache key generation
# ---------------------------------------------------------------------------


class TestCacheKey:
    def test_same_inputs_same_key(self):
        k1 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o-mini")
        k2 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o-mini")
        assert k1 == k2

    def test_different_url_different_key(self):
        k1 = _make_cache_key("https://example.com/a", "concise", "openai", "gpt-4o-mini")
        k2 = _make_cache_key("https://example.com/b", "concise", "openai", "gpt-4o-mini")
        assert k1 != k2

    def test_different_style_different_key(self):
        k1 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o-mini")
        k2 = _make_cache_key("https://example.com", "detailed", "openai", "gpt-4o-mini")
        assert k1 != k2

    def test_different_provider_different_key(self):
        k1 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o-mini")
        k2 = _make_cache_key("https://example.com", "concise", "anthropic", "gpt-4o-mini")
        assert k1 != k2

    def test_different_model_different_key(self):
        k1 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o-mini")
        k2 = _make_cache_key("https://example.com", "concise", "openai", "gpt-4")
        assert k1 != k2

    def test_url_is_normalized(self):
        k1 = _make_cache_key("HTTPS://EXAMPLE.COM/", "concise", "openai", "gpt-4o-mini")
        k2 = _make_cache_key("https://example.com/", "concise", "openai", "gpt-4o-mini")
        assert k1 == k2

    def test_key_is_hex_string(self):
        key = _make_cache_key("https://example.com", "concise", "openai", "gpt-4o-mini")
        assert len(key) == 64
        int(key, 16)  # should not raise


# ---------------------------------------------------------------------------
# SummaryCache – disabled mode
# ---------------------------------------------------------------------------


class TestSummaryCacheDisabled:
    def test_get_returns_none_when_disabled(self):
        cache = SummaryCache(enabled=False)
        result = cache.get("https://example.com", "concise", "openai", "gpt-4o-mini")
        assert result is None

    def test_set_is_noop_when_disabled(self):
        cache = SummaryCache(enabled=False)
        # Should not raise
        cache.set("https://example.com", "concise", "openai", "gpt-4o-mini", _make_summary())

    def test_clear_returns_zero_when_disabled(self):
        cache = SummaryCache(enabled=False)
        assert cache.clear() == 0


# ---------------------------------------------------------------------------
# SummaryCache – enabled mode (requires diskcache)
# ---------------------------------------------------------------------------


diskcache = pytest.importorskip("diskcache", reason="diskcache not installed")


class TestSummaryCacheEnabled:
    def test_cache_miss(self, tmp_path):
        with SummaryCache(cache_dir=tmp_path) as cache:
            result = cache.get("https://example.com", "concise", "openai", "gpt-4o-mini")
        assert result is None

    def test_cache_hit(self, tmp_path):
        summary = _make_summary()
        with SummaryCache(cache_dir=tmp_path) as cache:
            cache.set("https://example.com", "concise", "openai", "gpt-4o-mini", summary)
            result = cache.get("https://example.com", "concise", "openai", "gpt-4o-mini")

        assert result is not None
        assert result.summary == summary.summary
        assert result.title == summary.title

    def test_cache_hit_survives_reopen(self, tmp_path):
        summary = _make_summary()
        with SummaryCache(cache_dir=tmp_path) as cache:
            cache.set("https://example.com", "concise", "openai", "gpt-4o-mini", summary)

        # Open a fresh cache instance pointing at the same directory
        with SummaryCache(cache_dir=tmp_path) as cache2:
            result = cache2.get("https://example.com", "concise", "openai", "gpt-4o-mini")
        assert result is not None
        assert result.summary == summary.summary

    def test_different_styles_do_not_collide(self, tmp_path):
        s1 = _make_summary(style="concise", summary="Short.")
        s2 = _make_summary(style="detailed", summary="Much longer detailed summary.")

        with SummaryCache(cache_dir=tmp_path) as cache:
            cache.set("https://example.com", "concise", "openai", "gpt-4o-mini", s1)
            cache.set("https://example.com", "detailed", "openai", "gpt-4o-mini", s2)

            r1 = cache.get("https://example.com", "concise", "openai", "gpt-4o-mini")
            r2 = cache.get("https://example.com", "detailed", "openai", "gpt-4o-mini")

        assert r1.summary == "Short."
        assert r2.summary == "Much longer detailed summary."

    def test_ttl_expiry(self, tmp_path, monkeypatch):
        """Simulate TTL expiry by patching the env var to 0 hours (immediate expiry)."""
        monkeypatch.setenv("CACHE_TTL_HOURS", "0.000001")  # ~3.6ms TTL

        summary = _make_summary()
        with SummaryCache(cache_dir=tmp_path) as cache:
            cache.set("https://example.com", "concise", "openai", "gpt-4o-mini", summary)
            time.sleep(0.05)  # wait > 3.6ms
            result = cache.get("https://example.com", "concise", "openai", "gpt-4o-mini")

        assert result is None, "Expired entry should not be returned"

    def test_clear(self, tmp_path):
        summary = _make_summary()
        with SummaryCache(cache_dir=tmp_path) as cache:
            cache.set("https://example.com", "concise", "openai", "gpt-4o-mini", summary)
            count = cache.clear()
            assert count >= 1
            result = cache.get("https://example.com", "concise", "openai", "gpt-4o-mini")
        assert result is None

    def test_collision_resistance(self, tmp_path):
        """Keys that differ only in one field must not collide."""
        urls = [
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        ]
        with SummaryCache(cache_dir=tmp_path) as cache:
            for i, url in enumerate(urls):
                cache.set(url, "concise", "openai", "gpt-4o-mini", _make_summary(url=url, summary=f"Summary {i}"))

            for i, url in enumerate(urls):
                result = cache.get(url, "concise", "openai", "gpt-4o-mini")
                assert result is not None
                assert result.summary == f"Summary {i}"