"""
Tests for TokenBucket and RateLimiter: burst, sustained load, timeout, and token adjustment.
"""

import threading
import time

import pytest

from summarizer.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    TokenBucket,
    get_rate_limiter,
    reset_rate_limiters,
)


# ---------------------------------------------------------------------------
# TokenBucket tests
# ---------------------------------------------------------------------------


class TestTokenBucket:
    def test_starts_full(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.available_tokens() == pytest.approx(10.0, abs=0.1)

    def test_consume_single_token(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        result = bucket.consume(1.0)
        assert result is True
        assert bucket.available_tokens() == pytest.approx(9.0, abs=0.1)

    def test_consume_all_tokens(self):
        bucket = TokenBucket(capacity=5.0, refill_rate=1.0)
        result = bucket.consume(5.0)
        assert result is True
        assert bucket.available_tokens() == pytest.approx(0.0, abs=0.1)

    def test_consume_zero_tokens_always_succeeds(self):
        bucket = TokenBucket(capacity=0.0, refill_rate=0.1)
        assert bucket.consume(0) is True
        assert bucket.consume(-1) is True

    def test_refill_over_time(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=10.0)  # 10 tokens/sec
        bucket.consume(10.0)  # drain
        assert bucket.available_tokens() == pytest.approx(0.0, abs=0.5)
        time.sleep(0.5)  # should refill ~5 tokens
        assert bucket.available_tokens() == pytest.approx(5.0, abs=1.0)

    def test_refill_does_not_exceed_capacity(self):
        bucket = TokenBucket(capacity=5.0, refill_rate=100.0)
        time.sleep(0.2)  # would add 20 tokens without a cap
        assert bucket.available_tokens() <= 5.0 + 0.1  # small tolerance

    def test_blocking_consume_waits_for_refill(self):
        bucket = TokenBucket(capacity=5.0, refill_rate=10.0)  # 10 tokens/sec
        bucket.consume(5.0)  # drain completely

        start = time.monotonic()
        result = bucket.consume(1.0)  # should wait ~0.1s
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed >= 0.05  # at least some waiting happened

    def test_timeout_returns_false_when_not_enough_tokens(self):
        bucket = TokenBucket(capacity=1.0, refill_rate=0.01)  # very slow refill
        bucket.consume(1.0)  # drain

        result = bucket.consume(1.0, timeout=0.1)
        assert result is False

    def test_timeout_succeeds_if_tokens_available_in_time(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=20.0)  # fast refill
        bucket.consume(10.0)  # drain

        result = bucket.consume(1.0, timeout=2.0)  # should refill quickly
        assert result is True

    def test_burst_capacity_allows_initial_burst(self):
        bucket = TokenBucket(capacity=100.0, refill_rate=1.0)
        # Should be able to consume all 100 at once without waiting
        result = bucket.consume(100.0)
        assert result is True

    def test_multiple_threads_safe(self):
        """Token bucket should be thread-safe."""
        bucket = TokenBucket(capacity=100.0, refill_rate=50.0)
        consumed = []
        errors = []

        def worker():
            try:
                if bucket.consume(1.0, timeout=5.0):
                    consumed.append(1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(consumed) == 50

    def test_successive_consumes_deplete_bucket(self):
        bucket = TokenBucket(capacity=3.0, refill_rate=0.1)  # slow refill
        assert bucket.consume(1.0) is True
        assert bucket.consume(1.0) is True
        assert bucket.consume(1.0) is True
        # 4th should time out (capacity = 3, very slow refill)
        result = bucket.consume(1.0, timeout=0.05)
        assert result is False


# ---------------------------------------------------------------------------
# RateLimiter tests
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def setup_method(self):
        reset_rate_limiters()

    def teardown_method(self):
        reset_rate_limiters()

    def test_acquire_returns_true_under_limit(self):
        config = RateLimitConfig(requests_per_minute=60, tokens_per_minute=100_000)
        limiter = RateLimiter(config=config, provider="test")
        result = limiter.acquire(estimated_tokens=100)
        assert result is True

    def test_acquire_with_no_tokens(self):
        config = RateLimitConfig(requests_per_minute=60, tokens_per_minute=100_000)
        limiter = RateLimiter(config=config, provider="test")
        result = limiter.acquire(estimated_tokens=0)
        assert result is True

    def test_acquire_timeout_when_rate_exceeded(self):
        # 1 RPM with no burst — will exhaust quickly
        config = RateLimitConfig(
            requests_per_minute=1,
            tokens_per_minute=100_000,
            burst_multiplier=1.0,
        )
        limiter = RateLimiter(config=config, provider="test")
        # First acquire consumes the single request token
        limiter.acquire(estimated_tokens=0, timeout=1.0)
        # Second should time out
        result = limiter.acquire(estimated_tokens=0, timeout=0.1)
        assert result is False

    def test_available_requests_decreases_after_acquire(self):
        config = RateLimitConfig(
            requests_per_minute=60,
            tokens_per_minute=1_000_000,
            burst_multiplier=1.0,  # no burst
        )
        limiter = RateLimiter(config=config, provider="test")
        before = limiter.available_requests
        limiter.acquire(estimated_tokens=0)
        after = limiter.available_requests
        assert after < before

    def test_available_tokens_decreases_after_acquire(self):
        config = RateLimitConfig(requests_per_minute=1000, tokens_per_minute=10_000)
        limiter = RateLimiter(config=config, provider="test")
        before = limiter.available_tokens
        limiter.acquire(estimated_tokens=500)
        after = limiter.available_tokens
        assert after < before

    def test_record_actual_tokens_adjusts_bucket_upward(self):
        config = RateLimitConfig(requests_per_minute=1000, tokens_per_minute=10_000)
        limiter = RateLimiter(config=config, provider="test")
        limiter.acquire(estimated_tokens=100)
        before = limiter.available_tokens
        # Actual was less than estimated — tokens should be returned
        limiter.record_actual_tokens(actual_tokens=50, estimated_tokens=100)
        after = limiter.available_tokens
        assert after > before

    def test_record_actual_tokens_adjusts_bucket_downward(self):
        config = RateLimitConfig(requests_per_minute=1000, tokens_per_minute=10_000)
        limiter = RateLimiter(config=config, provider="test")
        limiter.acquire(estimated_tokens=100)
        before = limiter.available_tokens
        # Actual was more than estimated — extra tokens should be consumed
        limiter.record_actual_tokens(actual_tokens=200, estimated_tokens=100)
        after = limiter.available_tokens
        assert after < before

    def test_record_actual_tokens_same_is_noop(self):
        config = RateLimitConfig(requests_per_minute=1000, tokens_per_minute=10_000)
        limiter = RateLimiter(config=config, provider="test")
        limiter.acquire(estimated_tokens=100)
        before = limiter.available_tokens
        limiter.record_actual_tokens(actual_tokens=100, estimated_tokens=100)
        after = limiter.available_tokens
        # Should be essentially the same (within floating point tolerance)
        assert abs(after - before) < 1.0


# ---------------------------------------------------------------------------
# get_rate_limiter registry
# ---------------------------------------------------------------------------


class TestRateLimiterRegistry:
    def setup_method(self):
        reset_rate_limiters()

    def teardown_method(self):
        reset_rate_limiters()

    def test_same_provider_returns_same_instance(self):
        l1 = get_rate_limiter("openai")
        l2 = get_rate_limiter("openai")
        assert l1 is l2

    def test_different_providers_return_different_instances(self):
        l1 = get_rate_limiter("openai")
        l2 = get_rate_limiter("anthropic")
        assert l1 is not l2

    def test_provider_name_is_case_insensitive(self):
        l1 = get_rate_limiter("OpenAI")
        l2 = get_rate_limiter("openai")
        assert l1 is l2

    def test_reset_clears_registry(self):
        l1 = get_rate_limiter("openai")
        reset_rate_limiters()
        l2 = get_rate_limiter("openai")
        assert l1 is not l2

    def test_custom_config_applied_on_first_call(self):
        config = RateLimitConfig(requests_per_minute=5, tokens_per_minute=5_000)
        limiter = get_rate_limiter("custom_provider", config=config)
        assert limiter.config.requests_per_minute == 5
        assert limiter.config.tokens_per_minute == 5_000


# ---------------------------------------------------------------------------
# Sustained load simulation
# ---------------------------------------------------------------------------


class TestSustainedLoad:
    def test_sustained_requests_within_rpm(self):
        """
        Fire 5 requests at 60 RPM — should all succeed without blocking significantly.
        """
        config = RateLimitConfig(
            requests_per_minute=60,
            tokens_per_minute=1_000_000,
            burst_multiplier=2.0,
        )
        limiter = RateLimiter(config=config, provider="test_sustained")
        start = time.monotonic()
        for _ in range(5):
            result = limiter.acquire(estimated_tokens=100, timeout=2.0)
            assert result is True
        elapsed = time.monotonic() - start
        # 5 requests at 60 RPM with 2x burst should complete in well under 1 second
        assert elapsed < 1.0

    def test_burst_then_rate_limited(self):
        """
        Burst capacity should be exhausted, causing subsequent requests to be rate-limited.
        """
        config = RateLimitConfig(
            requests_per_minute=6,        # 0.1 req/sec
            tokens_per_minute=1_000_000,
            burst_multiplier=1.0,         # no burst
        )
        limiter = RateLimiter(config=config, provider="test_burst")
        # First request should succeed immediately
        assert limiter.acquire(estimated_tokens=0, timeout=0.5) is True
        # Second request should fail quickly (only 6 rpm = 0.1/s, timeout < refill time)
        result = limiter.acquire(estimated_tokens=0, timeout=0.05)
        assert result is False