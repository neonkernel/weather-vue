"""
Token-bucket rate limiter for controlling LLM API request and token throughput.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BucketConfig:
    """
    Configuration for a single token bucket.

    Attributes:
        rate:       tokens added per second
        capacity:   maximum burst capacity (tokens)
    """
    rate: float        # tokens / second
    capacity: float    # burst capacity


class TokenBucket:
    """
    Thread-safe token-bucket implementation.

    Supports both blocking (consume) and non-blocking (try_consume) modes.
    """

    def __init__(self, rate: float, capacity: float) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._rate = rate          # tokens per second
        self._capacity = capacity  # max tokens
        self._tokens = capacity    # start full
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        """Add tokens proportional to elapsed time (called under lock)."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        added = elapsed * self._rate
        self._tokens = min(self._capacity, self._tokens + added)
        self._last_refill = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    def try_consume(self, tokens: float = 1.0) -> bool:
        """
        Attempt to consume *tokens* without blocking.
        Returns True on success, False if insufficient tokens are available.
        """
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def consume(self, tokens: float = 1.0, timeout: Optional[float] = None) -> bool:
        """
        Block until *tokens* can be consumed or *timeout* seconds have elapsed.

        Returns True if tokens were consumed, False if timed out.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                # Calculate how long to sleep until enough tokens arrive
                deficit = tokens - self._tokens
                sleep_for = deficit / self._rate

            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                sleep_for = min(sleep_for, remaining)

            logger.debug("Rate limit: sleeping %.2fs for %.1f tokens", sleep_for, tokens)
            time.sleep(sleep_for)


class RateLimiter:
    """
    Composite rate limiter that enforces both requests-per-minute (RPM)
    and tokens-per-minute (TPM) limits for an LLM provider.

    Usage::

        limiter = RateLimiter(rpm=60, tpm=90_000)
        limiter.acquire(estimated_tokens=500)   # blocks if needed
        response = provider.complete(...)
    """

    def __init__(
        self,
        rpm: int = 60,
        tpm: int = 90_000,
        burst_rpm: Optional[int] = None,
        burst_tpm: Optional[int] = None,
    ) -> None:
        """
        Args:
            rpm:        Maximum requests per minute.
            tpm:        Maximum tokens per minute.
            burst_rpm:  Burst capacity for requests (defaults to rpm).
            burst_tpm:  Burst capacity for tokens (defaults to tpm).
        """
        req_rate = rpm / 60.0
        tok_rate = tpm / 60.0

        self._request_bucket = TokenBucket(
            rate=req_rate,
            capacity=float(burst_rpm if burst_rpm is not None else rpm),
        )
        self._token_bucket = TokenBucket(
            rate=tok_rate,
            capacity=float(burst_tpm if burst_tpm is not None else tpm),
        )
        self._rpm = rpm
        self._tpm = tpm

    def acquire(self, estimated_tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Block until both a request slot and *estimated_tokens* token budget
        are available, then consume them.

        Args:
            estimated_tokens: Expected number of tokens for the upcoming request.
            timeout:          Maximum seconds to wait (None = wait forever).

        Returns:
            True if acquired, False if timed out.
        """
        # Acquire request slot first
        if not self._request_bucket.consume(1.0, timeout=timeout):
            logger.warning("Rate limiter timed out waiting for a request slot")
            return False

        # Acquire token budget
        clamped = min(float(estimated_tokens), self._token_bucket._capacity)
        if not self._token_bucket.consume(clamped, timeout=timeout):
            logger.warning("Rate limiter timed out waiting for token budget")
            # Return the request slot we already consumed (best-effort)
            self._request_bucket._tokens = min(
                self._request_bucket._capacity,
                self._request_bucket._tokens + 1.0,
            )
            return False

        return True

    def try_acquire(self, estimated_tokens: int = 1) -> bool:
        """Non-blocking variant. Returns False immediately if rate-limited."""
        if not self._request_bucket.try_consume(1.0):
            return False
        clamped = min(float(estimated_tokens), self._token_bucket._capacity)
        if not self._token_bucket.try_consume(clamped):
            self._request_bucket._tokens = min(
                self._request_bucket._capacity,
                self._request_bucket._tokens + 1.0,
            )
            return False
        return True


# ---------------------------------------------------------------------------
# Provider-specific default limits
# ---------------------------------------------------------------------------

_PROVIDER_DEFAULTS: dict[str, dict[str, int]] = {
    "openai": {"rpm": 500, "tpm": 150_000},
    "anthropic": {"rpm": 50, "tpm": 40_000},
    "gemini": {"rpm": 60, "tpm": 60_000},
    "ollama": {"rpm": 120, "tpm": 200_000},  # local — generous defaults
}


def create_rate_limiter(provider: str) -> RateLimiter:
    """
    Create a RateLimiter pre-configured with sensible defaults for *provider*.
    Defaults can be overridden via environment variables:

        SUMMARIZER_RPM, SUMMARIZER_TPM
    """
    import os

    defaults = _PROVIDER_DEFAULTS.get(provider.lower(), {"rpm": 60, "tpm": 60_000})
    rpm = int(os.environ.get("SUMMARIZER_RPM", defaults["rpm"]))
    tpm = int(os.environ.get("SUMMARIZER_TPM", defaults["tpm"]))
    logger.debug("Rate limiter for %s: rpm=%d tpm=%d", provider, rpm, tpm)
    return RateLimiter(rpm=rpm, tpm=tpm)