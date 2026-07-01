"""Tests for the TokenBucket rate limiter."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from src.summarizer.rate_limiter import (
    RateLimitConfig,
    TokenBucket,
    get_rate_limiter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fast_bucket(rpm: float = 60.0, tpm: float = 6000.0) -> TokenBucket:
    """Return a bucket with configurable limits."""
    return TokenBucket(RateLimitConfig(requests_per_minute=rpm, tokens_per_minute=tpm))


# ---------------------------------------------------------------------------
# Basic acquisition
# ---------------------------------------------------------------------------


class TestTokenBucketBasic:
    def test_immediate_acquire_succeeds(self):
        bucket = _fast_bucket()
        # Should not raise or sleep
        bucket.acquire()

    def test_try_acquire_returns_true_when_available(self):
        bucket = _fast_bucket()
        assert bucket.try_acquire() is True

    def test_try_acquire_returns_false_when_empty(self):
        # Start with a bucket that is immediately empty after one request
        bucket = TokenBucket(RateLimitConfig(requests_per_minute=0.001, tokens_per_minute=100))
        # Force the bucket to be nearly empty
        bucket._req_tokens = 0.5
        assert bucket.try_acquire() is False

    def test_multiple_quick_acquires_respect_limit(self):
        # Very low RPM so we exhaust quickly
        bucket = _fast_bucket(rpm=3.0)
        bucket.acquire()
        bucket.acquire()
        bucket.acquire()
        # 4th acquire should find bucket empty
        assert bucket.try_acquire() is False

    def test_token_budget_respected(self):
        bucket = _fast_bucket(rpm=100, tpm=100)
        assert bucket.try_acquire(estimated_tokens=50) is True
        assert bucket.try_acquire(estimated_tokens=50) is True
        # 101 tokens consumed, should fail
        assert bucket.try_acquire(estimated_tokens=1) is False

    def test_zero_estimated_tokens_skips_tpm(self):
        """estimated_tokens=0 should skip the token bucket check."""
        bucket = _fast_bucket(rpm=100, tpm=0.001)
        # tpm is essentially 0 but estimated_tokens=0 means we don't check it
        bucket._tok_tokens = 0.0
        assert bucket.try_acquire(estimated_tokens=0) is True


# ---------------------------------------------------------------------------
# Refill behaviour
# ---------------------------------------------------------------------------


class TestTokenBucketRefill:
    def test_refills_over_time(self):
        bucket = _fast_bucket(rpm=60.0)
        # Drain the request bucket
        bucket._req_tokens = 0.0
        bucket._req_last = time.monotonic()

        # Simulate 1 second passing (= 1 token at 60 RPM)
        with patch("time.monotonic", return_value=bucket._req_last + 1.0):
            bucket._refill()
        assert bucket._req_tokens == pytest.approx(1.0, abs=0.01)

    def test_refill_does_not_exceed_capacity(self):
        bucket = _fast_bucket(rpm=60.0)
        bucket._req_tokens = 59.9
        bucket._req_last = time.monotonic() - 100  # 100 seconds elapsed

        bucket._refill()
        assert bucket._req_tokens == pytest.approx(60.0, abs=0.01)

    def test_tpm_refills_proportionally(self):
        bucket = _fast_bucket(rpm=60.0, tpm=6000.0)
        bucket._tok_tokens = 0.0
        t0 = time.monotonic()
        bucket._tok_last = t0

        # 30 seconds elapsed → half the per-minute allowance = 3000 tokens
        with patch("time.monotonic", return_value=t0 + 30.0):
            bucket._refill()
        assert bucket._tok_tokens == pytest.approx(3000.0, abs=1.0)


# ---------------------------------------------------------------------------
# Blocking acquire with mocked sleep
# ---------------------------------------------------------------------------


class TestTokenBucketBlocking:
    def test_acquire_sleeps_when_exhausted(self):
        bucket = _fast_bucket(rpm=60.0)
        bucket._req_tokens = 0.0
        t0 = time.monotonic()
        bucket._req_last = t0

        sleep_calls: list[float] = []

        def fake_sleep(secs: float) -> None:
            sleep_calls.append(secs)
            # Simulate refill by advancing _req_last
            bucket._req_last = time.monotonic() - secs
            bucket._req_tokens = 1.0

        with patch("src.summarizer.rate_limiter.time.sleep", side_effect=fake_sleep):
            bucket.acquire()

        assert len(sleep_calls) >= 1

    def test_acquire_waits_for_both_buckets(self):
        """acquire() should wait when tokens-per-minute is exhausted too."""
        bucket = _fast_bucket(rpm=100, tpm=10)
        bucket._tok_tokens = 0.0

        sleep_calls: list[float] = []

        def fake_sleep(secs: float) -> None:
            sleep_calls.append(secs)
            bucket._tok_tokens = 100.0  # Simulate refill

        with patch("src.summarizer.rate_limiter.time.sleep", side_effect=fake_sleep):
            bucket.acquire(estimated_tokens=5)

        assert len(sleep_calls) >= 1


# ---------------------------------------------------------------------------
# Burst behaviour
# ---------------------------------------------------------------------------


class TestTokenBucketBurst:
    def test_burst_up_to_capacity(self):
        """A full bucket allows a burst equal to its capacity."""
        bucket = _fast_bucket(rpm=10.0)
        # Bucket starts full (10 tokens)
        successes = sum(bucket.try_acquire() for _ in range(10))
        assert successes == 10
        # Next one should fail
        assert bucket.try_acquire() is False

    def test_sustained_load(self):
        """
        After a burst drains the bucket, tokens should refill.
        We fake time.monotonic to avoid actual sleeps.
        """
        bucket = _fast_bucket(rpm=60.0)
        # Drain
        for _ in range(60):
            bucket.try_acquire()
        assert bucket.try_acquire() is False

        # Advance clock by 1 second → should have 1 new token
        bucket._req_last -= 1.0
        assert bucket.try_acquire() is True


# ---------------------------------------------------------------------------
# get_rate_limiter factory
# ---------------------------------------------------------------------------


class TestGetRateLimiter:
    def test_known_provider_returns_configured_bucket(self):
        bucket = get_rate_limiter("openai")
        assert isinstance(bucket, TokenBucket)
        assert bucket._rpm == pytest.approx(60.0)

    def test_unknown_provider_returns_default_bucket(self):
        bucket = get_rate_limiter("some_unknown_provider")
        assert isinstance(bucket, TokenBucket)

    def test_case_insensitive(self):
        b1 = get_rate_limiter("OpenAI")
        b2 = get_rate_limiter("openai")
        assert b1._rpm == b2._rpm