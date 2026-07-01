"""Token bucket rate limiter for API calls."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Per-provider rate limit configuration."""

    requests_per_minute: float = 60.0
    tokens_per_minute: float = 90_000.0


# Sensible defaults for well-known providers
PROVIDER_DEFAULTS: dict[str, RateLimitConfig] = {
    "openai": RateLimitConfig(requests_per_minute=60, tokens_per_minute=90_000),
    "anthropic": RateLimitConfig(requests_per_minute=50, tokens_per_minute=100_000),
    "ollama": RateLimitConfig(requests_per_minute=120, tokens_per_minute=200_000),
}


class TokenBucket:
    """
    Thread-safe token bucket for rate limiting.

    Supports two independent buckets:
      - request bucket  (1 token consumed per API call)
      - token bucket    (N tokens consumed per API call based on estimated usage)
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        cfg = config or RateLimitConfig()
        self._rpm = cfg.requests_per_minute
        self._tpm = cfg.tokens_per_minute

        # Request bucket state
        self._req_tokens: float = self._rpm
        self._req_last: float = time.monotonic()

        # Token bucket state
        self._tok_tokens: float = self._tpm
        self._tok_last: float = time.monotonic()

        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        """Refill both buckets based on elapsed time (called with lock held)."""
        now = time.monotonic()

        req_elapsed = now - self._req_last
        self._req_tokens = min(
            self._rpm,
            self._req_tokens + req_elapsed * (self._rpm / 60.0),
        )
        self._req_last = now

        tok_elapsed = now - self._tok_last
        self._tok_tokens = min(
            self._tpm,
            self._tok_tokens + tok_elapsed * (self._tpm / 60.0),
        )
        self._tok_last = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self, estimated_tokens: int = 0) -> None:
        """
        Block until both a request slot and token budget are available.

        Parameters
        ----------
        estimated_tokens:
            Rough estimate of tokens this request will consume.
            If 0, only the request-per-minute limit is enforced.
        """
        while True:
            with self._lock:
                self._refill()

                req_ok = self._req_tokens >= 1.0
                tok_ok = estimated_tokens == 0 or self._tok_tokens >= estimated_tokens

                if req_ok and tok_ok:
                    self._req_tokens -= 1.0
                    if estimated_tokens:
                        self._tok_tokens -= estimated_tokens
                    logger.debug(
                        "Rate limiter acquired (req_remaining=%.1f, tok_remaining=%.0f)",
                        self._req_tokens,
                        self._tok_tokens,
                    )
                    return

                # Calculate how long we need to wait
                waits: list[float] = []
                if not req_ok:
                    deficit = 1.0 - self._req_tokens
                    waits.append(deficit / (self._rpm / 60.0))
                if not tok_ok and estimated_tokens:
                    deficit = estimated_tokens - self._tok_tokens
                    waits.append(deficit / (self._tpm / 60.0))

                wait_secs = max(waits) if waits else 0.1

            logger.debug("Rate limit reached; sleeping %.2fs", wait_secs)
            time.sleep(wait_secs)

    def try_acquire(self, estimated_tokens: int = 0) -> bool:
        """Non-blocking version; returns False if tokens are not available."""
        with self._lock:
            self._refill()
            req_ok = self._req_tokens >= 1.0
            tok_ok = estimated_tokens == 0 or self._tok_tokens >= estimated_tokens
            if req_ok and tok_ok:
                self._req_tokens -= 1.0
                if estimated_tokens:
                    self._tok_tokens -= estimated_tokens
                return True
            return False


def get_rate_limiter(provider: str) -> TokenBucket:
    """Return a TokenBucket configured with provider-specific defaults."""
    config = PROVIDER_DEFAULTS.get(provider.lower(), RateLimitConfig())
    return TokenBucket(config)