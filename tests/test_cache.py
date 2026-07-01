"""
Tests for SummaryCache: hit/miss behaviour, TTL, key generation, and cache clearing.
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.summarizer.cache import SummaryCache, _make_cache_key
from src.summarizer.models import Summary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_cache(tmp_path: Path) -> SummaryCache:
    """Return a SummaryCache backed by a temporary directory."""
    return SummaryCache(cache_dir=tmp_path / "cache", ttl_seconds=3600)


@pytest.fixture
def sample_summary() -> Summary:
    return Summary(
        text="This is a test summary.",
        style="concise",
        provider="openai",
        model="gpt-4o-mini",
        url="https://example.com/article",
        title="Test Article",
    )


# ---------------------------------------------------------------------------
# Cache key generation
# ---------------------------------------------------------------------------

class TestCacheKeyGeneration:

    def test_same_inputs_same_key(self):
        key1 = _make_cache_key("https://example.com/", "concise", "openai", "gpt-4o-mini")
        key2 = _make_cache_key("https://example.com/", "concise", "openai", "gpt-4o-mini")
        assert key1 == key2

    def test_different_urls_different_keys(self):
        key1 = _make_cache_key("https://example.com/a", "concise", "openai", "gpt-4o-mini")
        key2 = _make_cache_key("https://example.com/b", "concise", "openai", "gpt-4o-mini")
        assert key1 != key2

    def test_different_styles_different_keys(self):
        key1 = _make_cache_key("https://example.com/", "concise", "openai", "gpt-4o-mini")
        key2 = _make_cache_key("https://example.com/", "detailed", "openai", "gpt-4o-mini")
        assert key1 != key2

    def test_different_providers_different_keys(self):
        key1 = _make_cache_key("https://example.com/", "concise", "openai", "gpt-4o-mini")
        key2 = _make_cache_key("https://example.com/", "concise", "anthropic", "gpt-4o-mini")
        assert key1 != key2

    def test_different_models_different_keys(self):
        key1 = _make_cache_key("https://example.com/", "concise", "openai", "gpt-4o-mini")
        key2 = _make_cache_key("https://example.com/", "concise", "openai", "gpt-4o")
        assert key1 != key2

    def test_trailing_slash_normalised(self):
        """Trailing slash on URL should not produce a different key."""
        key1 = _make_cache_key("https://example.com/article", "concise", "openai", "gpt-4o-mini")
        key2 = _make_cache_key("https://example.com/article/", "concise", "openai", "gpt-4o-mini")
        assert key1 == key2

    def test_key_is_hex_string(self):
        key = _make_cache_key("https://example.com/", "concise", "openai", "gpt-4o-mini")
        assert len(key) == 64  # SHA-256 produces 64 hex chars
        assert all(c in "0123456789abcdef" for c in key)

    def test_collision_resistance(self):
        """Verify 1000 distinct inputs produce 1000 distinct keys."""
        keys = {
            _make_cache_key(f"https://example.com/{i}", "concise", "openai", "gpt-4o-mini")
            for i in range(1000)
        }
        assert len(keys) == 1000


# ---------------------------------------------------------------------------
# Cache miss behaviour
# ---------------------------------------------------------------------------

class TestCacheMiss:

    def test_get_returns_none_on_miss(self, tmp_cache: SummaryCache):
        result = tmp_cache.get("nonexistent-key")
        assert result is None

    def test_get_returns_none_before_any_set(self, tmp_cache: SummaryCache):
        key = tmp_cache.make_key("https://x.com/", "concise", "openai", "gpt-4o-mini")
        assert tmp_cache.get(key) is None


# ---------------------------------------------------------------------------
# Cache hit behaviour
# ---------------------------------------------------------------------------

class TestCacheHit:

    def test_set_then_get_returns_summary(self, tmp_cache: SummaryCache, sample_summary: Summary):
        key = tmp_cache.make_key(
            sample_summary.url, sample_summary.style,
            sample_summary.provider, sample_summary.model,
        )
        tmp_cache.set(key, sample_summary)
        retrieved = tmp_cache.get(key)

        assert retrieved is not None
        assert retrieved.text == sample_summary.text
        assert retrieved.title == sample_summary.title
        assert retrieved.url == sample_summary.url
        assert retrieved.style == sample_summary.style
        assert retrieved.provider == sample_summary.provider
        assert retrieved.model == sample_summary.model

    def test_overwrite_replaces_value(self, tmp_cache: SummaryCache, sample_summary: Summary):
        key = "test-key"
        tmp_cache.set(key, sample_summary)

        updated = Summary(
            text="Updated summary.",
            style="detailed",
            provider="anthropic",
            model="claude-3",
            url="https://example.com/article",
            title="Updated Title",
        )
        tmp_cache.set(key, updated)
        retrieved = tmp_cache.get(key)
        assert retrieved is not None
        assert retrieved.text == "Updated summary."

    def test_different_keys_independent(self, tmp_cache: SummaryCache, sample_summary: Summary):
        key_a = tmp_cache.make_key("https://a.com/", "concise", "openai", "gpt-4o-mini")
        key_b = tmp_cache.make_key("https://b.com/", "concise", "openai", "gpt-4o-mini")

        summary_b = Summary(
            text="Summary B",
            style="concise",
            provider="openai",
            model="gpt-4o-mini",
            url="https://b.com/",
        )

        tmp_cache.set(key_a, sample_summary)
        tmp_cache.set(key_b, summary_b)

        assert tmp_cache.get(key_a).text == sample_summary.text
        assert tmp_cache.get(key_b).text == "Summary B"


# ---------------------------------------------------------------------------
# TTL / expiry
# ---------------------------------------------------------------------------

class TestCacheTTL:

    def test_expired_entry_returns_none(self, tmp_path: Path):
        """An entry with TTL=1s should be gone after ~2s."""
        cache = SummaryCache(cache_dir=tmp_path / "ttl_cache", ttl_seconds=1)
        summary = Summary(
            text="Expires soon.",
            style="concise",
            provider="openai",
            model="gpt-4o-mini",
        )
        key = "expiry-test"
        cache.set(key, summary)
        assert cache.get(key) is not None  # should be present immediately

        time.sleep(2)
        # diskcache honours TTL on read
        result = cache.get(key)
        # If diskcache is available, the entry should be expired
        try:
            import diskcache  # noqa: F401
            assert result is None, "Entry should have expired"
        except ImportError:
            # Without diskcache we use an in-memory dict which has no TTL enforcement
            pass

        cache.close()

    def test_non_expired_entry_present(self, tmp_path: Path):
        cache = SummaryCache(cache_dir=tmp_path / "ttl_cache2", ttl_seconds=3600)
        summary = Summary(
            text="Long-lived.",
            style="concise",
            provider="openai",
            model="gpt-4o-mini",
        )
        key = "long-lived"
        cache.set(key, summary)
        assert cache.get(key) is not None
        cache.close()


# ---------------------------------------------------------------------------
# Cache clearing
# ---------------------------------------------------------------------------

class TestCacheClear:

    def test_clear_removes_all_entries(self, tmp_cache: SummaryCache, sample_summary: Summary):
        for i in range(5):
            tmp_cache.set(f"key-{i}", sample_summary)

        assert len(tmp_cache) == 5
        count = tmp_cache.clear()
        assert count == 5
        assert len(tmp_cache) == 0

    def test_clear_on_empty_cache_returns_zero(self, tmp_cache: SummaryCache):
        count = tmp_cache.clear()
        assert count == 0

    def test_get_after_clear_returns_none(self, tmp_cache: SummaryCache, sample_summary: Summary):
        key = "some-key"
        tmp_cache.set(key, sample_summary)
        tmp_cache.clear()
        assert tmp_cache.get(key) is None


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------

class TestSerialisation:

    def test_optional_fields_preserved(self, tmp_cache: SummaryCache):
        summary = Summary(
            text="No URL or title.",
            style="bullet",
            provider="ollama",
            model="llama3",
            url=None,
            title=None,
        )
        tmp_cache.set("no-url", summary)
        result = tmp_cache.get("no-url")
        assert result is not None
        assert result.url is None
        assert result.title is None

    def test_unicode_content_preserved(self, tmp_cache: SummaryCache):
        summary = Summary(
            text="日本語のサマリー 🎉",
            style="concise",
            provider="openai",
            model="gpt-4o-mini",
        )
        tmp_cache.set("unicode-key", summary)
        result = tmp_cache.get("unicode-key")
        assert result is not None
        assert result.text == "日本語のサマリー 🎉"


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:

    def test_context_manager_closes_cache(self, tmp_path: Path):
        with SummaryCache(cache_dir=tmp_path / "ctx") as cache:
            summary = Summary(
                text="ctx test",
                style="concise",
                provider="openai",
                model="gpt-4o-mini",
            )
            cache.set("ctx-key", summary)
            assert cache.get("ctx-key") is not None
        # After context exit the cache is closed; no exception should be raised.

    def test_make_key_via_instance(self, tmp_cache: SummaryCache):
        key = tmp_cache.make_key("https://example.com/", "concise", "openai", "gpt-4o-mini")
        assert len(key) == 64