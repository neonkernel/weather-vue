"""
Token bucket rate limiter for API calls.
Supports requests-per-minute (RPM) and tokens-per-minute (TPM) limits.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting per provider."""
    requests_per_minute: int = 60          # max RPM
    tokens_per_minute: int = 90_000        # max TPM
    burst_multiplier: float = 1.5          # allow short bursts above sustained rate
    min_sleep_seconds: float = 0.05        # minimum sleep to avoid busy-wait


# Sensible defaults per provider
PROVIDER_DEFAULTS: dict[str, RateLimitConfig] = {
    "openai": RateLimitConfig(requests_per_minute=60, tokens_per_minute=90_000),
    "anthropic": RateLimitConfig(requests_per_minute=50, tokens_per_minute=100_000),
    "cohere": RateLimitConfig(requests_per_minute=100, tokens_per_minute=200_000),
    "ollama": RateLimitConfig(requests_per_minute=500, tokens_per_minute=1_000_000),
    "default": RateLimitConfig(requests_per_minute=60, tokens_per_minute=90_000),
}


class TokenBucket:
    """
    A token bucket algorithm implementation for rate limiting.

    The bucket refills at a constant rate (tokens / second).
    If the bucket has enough tokens, consume them immediately.
    If not, sleep until enough tokens are available.
    """

    def __init__(self, capacity: float, refill_rate: float):
        """
        Args:
            capacity: Maximum number of tokens in the bucket (burst capacity).
            refill_rate: Tokens added per second (sustained rate).
        """
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._tokens = float(capacity)  # start full
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill (must hold lock)."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        added = elapsed * self.refill_rate
        self._tokens = min(self.capacity, self._tokens + added)
        self._last_refill = now

    def consume(self, tokens: float = 1.0, timeout: Optional[float] = None) -> bool:
        """
        Consume `tokens` from the bucket, blocking until they are available.

        Args:
            tokens: Number of tokens to consume.
            timeout: Maximum seconds to wait. None = wait forever.

        Returns:
            True if tokens were consumed, False if timed out.
        """
        if tokens <= 0:
            return True

        deadline = (time.monotonic() + timeout) if timeout is not None else None

        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                # Calculate how long until we have enough tokens
                deficit = tokens - self._tokens
                wait_time = deficit / self.refill_rate

            # Check timeout
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.warning("Rate limit timeout waiting for %s tokens", tokens)
                    return False
                wait_time = min(wait_time, remaining)

            logger.debug("Rate limit: sleeping %.2fs for %s tokens", wait_time, tokens)
            time.sleep(max(wait_time, 0.001))

    def available_tokens(self) -> float:
        """Return the current number of available tokens (approximate)."""
        with self._lock:
            self._refill()
            return self._tokens


class RateLimiter:
    """
    Composite rate limiter that enforces both RPM and TPM limits using token buckets.
    Thread-safe and suitable for use across concurrent calls.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None, provider: str = "default"):
        if config is None:
            config = PROVIDER_DEFAULTS.get(provider.lower(), PROVIDER_DEFAULTS["default"])
        self.config = config
        self.provider = provider

        rpm_capacity = config.requests_per_minute * config.burst_multiplier
        rpm_rate = config.requests_per_minute / 60.0  # tokens per second

        tpm_capacity = config.tokens_per_minute * config.burst_multiplier
        tpm_rate = config.tokens_per_minute / 60.0  # tokens per second

        self._request_bucket = TokenBucket(capacity=rpm_capacity, refill_rate=rpm_rate)
        self._token_bucket = TokenBucket(capacity=tpm_capacity, refill_rate=tpm_rate)

        logger.debug(
            "RateLimiter initialized for %s: RPM=%d, TPM=%d",
            provider, config.requests_per_minute, config.tokens_per_minute
        )

    def acquire(self, estimated_tokens: int = 0, timeout: Optional[float] = None) -> bool:
        """
        Acquire rate limit slots for one API request with an estimated token count.

        Args:
            estimated_tokens: Estimated number of tokens for this request.
            timeout: Maximum seconds to wait. None = wait forever.

        Returns:
            True if slots acquired, False if timed out.
        """
        # First acquire a request slot
        if not self._request_bucket.consume(1.0, timeout=timeout):
            logger.warning("RateLimiter: timed out waiting for request slot (%s)", self.provider)
            return False

        # Then acquire token slots if we have an estimate
        if estimated_tokens > 0:
            if not self._token_bucket.consume(float(estimated_tokens), timeout=timeout):
                logger.warning(
                    "RateLimiter: timed out waiting for %d token slots (%s)",
                    estimated_tokens, self.provider
                )
                # We consumed a request slot but couldn't get tokens — release isn't possible
                # in a simple bucket, but the request slot will refill naturally.
                return False

        return True

    def record_actual_tokens(self, actual_tokens: int, estimated_tokens: int = 0) -> None:
        """
        Adjust the token bucket for the difference between estimated and actual token usage.
        Call this after a successful API response.

        Args:
            actual_tokens: Actual tokens used (from API response).
            estimated_tokens: Tokens pre-consumed in acquire().
        """
        diff = actual_tokens - estimated_tokens
        if diff > 0:
            # Used more than estimated — consume the extra
            self._token_bucket.consume(float(diff))
        elif diff < 0:
            # Used fewer — return the tokens (add back)
            with self._token_bucket._lock:
                self._token_bucket._tokens = min(
                    self._token_bucket.capacity,
                    self._token_bucket._tokens + abs(diff)
                )

    @property
    def available_requests(self) -> float:
        return self._request_bucket.available_tokens()

    @property
    def available_tokens(self) -> float:
        return self._token_bucket.available_tokens()


# Global registry of rate limiters (one per provider)
_limiters: dict[str, RateLimiter] = {}
_limiter_lock = threading.Lock()


def get_rate_limiter(provider: str, config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """
    Get or create a RateLimiter for the given provider.
    Config is only used when creating a new limiter.
    """
    key = provider.lower()
    with _limiter_lock:
        if key not in _limiters:
            _limiters[key] = RateLimiter(config=config, provider=key)
        return _limiters[key]


def reset_rate_limiters() -> None:
    """Reset all rate limiters (useful in tests)."""
    with _limiter_lock:
        _limiters.clear()