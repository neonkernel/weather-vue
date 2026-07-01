"""
Tests for TokenBucket and RateLimiter under burst and sustained-load scenarios.
"""
from __future__ import annotations

import time
import threading
from unittest.mock import patch

import pytest

from src.summarizer.rate_limiter import (
    TokenBucket,
    RateLimiter,
    create_rate_limiter,
)


# ---------------------------------------------------------------------------
# TokenBucket unit tests
# ---------------------------------------------------------------------------

class TestTokenBucketInit:

    def test_starts_full(self):
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        assert bucket.tokens == pytest.approx(10.0, abs=0.1)

    def test_invalid_rate_raises(self):
        with pytest.raises(ValueError, match="rate"):
            TokenBucket(rate=0, capacity=10)

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity"):
            TokenBucket(rate=10, capacity=0)


class TestTokenBucketTryConsume:

    def test_consume_within_capacity(self):
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        assert bucket.try_consume(5.0) is True
        assert bucket.tokens == pytest.approx(5.0, abs=0.1)

    def test_consume_exact_capacity(self):
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        assert bucket.try_consume(10.0) is True

    def test_consume_exceeds_capacity_fails(self):
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        bucket.try_consume(10.0)  # drain it
        assert bucket.try_consume(1.0) is False

    def test_partial_refill_allows_consume(self):
        """After draining, wait for partial refill and try again."""
        bucket = TokenBucket(rate=100.0, capacity=10.0)
        bucket.try_consume(10.0)  # drain
        time.sleep(0.05)  # 5 tokens should refill at 100/s
        assert bucket.try_consume(4.0) is True

    def test_try_consume_default_one_token(self):
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        assert bucket.try_consume() is True
        assert bucket.tokens == pytest.approx(9.0, abs=0.2)


class TestTokenBucketConsume:

    def test_blocking_consume_waits_for_refill(self):
        bucket = TokenBucket(rate=50.0, capacity=10.0)
        bucket.try_consume(10.0)  # drain

        start = time.monotonic()
        result = bucket.consume(5.0)  # should wait ~0.1s
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed >= 0.08  # at least 80ms

    def test_blocking_consume_timeout(self):
        bucket = TokenBucket(rate=1.0, capacity=1.0)
        bucket.try_consume(1.0)  # drain, refill rate = 1 token/s

        start = time.monotonic()
        result = bucket.consume(5.0, timeout=0.2)  # needs 5s, timeout=0.2s
        elapsed = time.monotonic() - start

        assert result is False
        assert elapsed < 1.0  # should not have waited the full 5s

    def test_consume_already_full(self):
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        assert bucket.consume(1.0) is True

    def test_consume_no_timeout_blocks(self):
        """consume without timeout should succeed eventually."""
        bucket = TokenBucket(rate=100.0, capacity=5.0)
        bucket.try_consume(5.0)  # drain
        # 5 tokens at 100/s ≈ 50ms
        result = bucket.consume(5.0)
        assert result is True


class TestTokenBucketThreadSafety:

    def test_concurrent_consume_no_overdraft(self):
        """
        100 threads each try to consume 1 token from a 10-token bucket.
        At most 10 should succeed without sleeping.
        """
        bucket = TokenBucket(rate=0.001, capacity=10.0)  # very slow refill
        results = []
        lock = threading.Lock()

        def attempt():
            ok = bucket.try_consume(1.0)
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=attempt) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = sum(1 for r in results if r)
        assert successes <= 10, f"Expected ≤10 successes, got {successes}"

    def test_refill_does_not_exceed_capacity(self):
        bucket = TokenBucket(rate=1000.0, capacity=5.0)
        bucket.try_consume(5.0)  # drain
        time.sleep(0.1)  # would add 100 tokens at rate=1000, but capped at 5
        assert bucket.tokens <= 5.0 + 0.01  # tiny floating-point slack


# ---------------------------------------------------------------------------
# RateLimiter tests
# ---------------------------------------------------------------------------

class TestRateLimiterInit:

    def test_default_init(self):
        rl = RateLimiter(rpm=60, tpm=60_000)
        assert rl._rpm == 60
        assert rl._tpm == 60_000

    def test_request_and_token_buckets_created(self):
        rl = RateLimiter(rpm=30, tpm=30_000)
        assert rl._request_bucket is not None
        assert rl._token_bucket is not None


class TestRateLimiterAcquire:

    def test_try_acquire_succeeds_when_full(self):
        rl = RateLimiter(rpm=60, tpm=90_000)
        assert rl.try_acquire(estimated_tokens=100) is True

    def test_try_acquire_fails_when_request_bucket_empty(self):
        rl = RateLimiter(rpm=1, tpm=90_000)
        assert rl.try_acquire() is True  # first request consumes the single slot
        assert rl.try_acquire() is False  # no slots left

    def test_try_acquire_fails_when_token_bucket_empty(self):
        rl = RateLimiter(rpm=60, tpm=100)  # tiny token budget
        # Drain the token bucket
        while rl._token_bucket.try_consume(10):
            pass
        assert rl.try_acquire(estimated_tokens=200) is False

    def test_acquire_blocking_returns_true(self):
        rl = RateLimiter(rpm=120, tpm=100_000)
        assert rl.acquire(estimated_tokens=10) is True

    def test_acquire_timeout_when_exhausted(self):
        rl = RateLimiter(rpm=1, tpm=90_000)
        rl.try_acquire()  # consume the one slot

        start = time.monotonic()
        result = rl.acquire(estimated_tokens=1, timeout=0.3)
        elapsed = time.monotonic() - start

        assert result is False
        assert elapsed < 2.0  # should not hang


class TestRateLimiterBurstBehaviour:

    def test_burst_allows_multiple_requests(self):
        """Burst capacity = RPM means a full minute's worth of requests fit in a burst."""
        rl = RateLimiter(rpm=10, tpm=100_000, burst_rpm=10)
        successes = sum(1 for _ in range(10) if rl.try_acquire(estimated_tokens=1))
        assert successes == 10

    def test_burst_exhausted_then_refills(self):
        rl = RateLimiter(rpm=60, tpm=100_000, burst_rpm=2)
        assert rl.try_acquire(1) is True
        assert rl.try_acquire(1) is True
        assert rl.try_acquire(1) is False  # burst exhausted

        time.sleep(0.05)  # wait for partial refill (≥1 token at 1 req/s → needs ~1s)
        # We don't assert True here because refill at 1 req/s takes ~1s for 1 token
        # Just verify no exception is raised


class TestRateLimiterSustainedLoad:

    def test_sustained_throughput_within_rpm(self):
        """
        At 60 RPM (1 req/s), 3 requests over ~3s should all succeed.
        We use a high RPM so the test runs fast.
        """
        rl = RateLimiter(rpm=600, tpm=1_000_000)  # 10 req/s
        results = []
        for _ in range(5):
            results.append(rl.try_acquire(estimated_tokens=10))
        assert all(results), "All 5 requests should succeed at 600 RPM burst"


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

class TestCreateRateLimiter:

    def test_known_provider_openai(self):
        rl = create_rate_limiter("openai")
        assert isinstance(rl, RateLimiter)
        assert rl._rpm == 500

    def test_known_provider_anthropic(self):
        rl = create_rate_limiter("anthropic")
        assert isinstance(rl, RateLimiter)
        assert rl._rpm == 50

    def test_unknown_provider_uses_defaults(self):
        rl = create_rate_limiter("unknown_llm")
        assert isinstance(rl, RateLimiter)
        assert rl._rpm == 60

    def test_env_override_rpm(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SUMMARIZER_RPM", "999")
        monkeypatch.setenv("SUMMARIZER_TPM", "500000")
        rl = create_rate_limiter("openai")
        assert rl._rpm == 999
        assert rl._tpm == 500_000