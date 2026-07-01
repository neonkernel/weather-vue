"""
Unified LLM client with integrated rate limiting.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from ..rate_limiter import RateLimiter, create_rate_limiter
from ..exceptions import SummarizerError

logger = logging.getLogger(__name__)

# Shared rate-limiter instances keyed by provider name so that multiple
# LLMClient instances targeting the same provider share quota.
_rate_limiters: dict[str, RateLimiter] = {}
_RL_ENABLED = os.environ.get("SUMMARIZER_RATE_LIMIT", "1") not in ("0", "false", "no")


def _get_rate_limiter(provider: str) -> Optional[RateLimiter]:
    if not _RL_ENABLED:
        return None
    if provider not in _rate_limiters:
        _rate_limiters[provider] = create_rate_limiter(provider)
    return _rate_limiters[provider]


class LLMClient:
    """
    Provider-agnostic LLM client.

    Wraps the actual provider implementation and gates every API call through
    the shared :class:`~summarizer.rate_limiter.RateLimiter` for the provider.
    """

    def __init__(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model
        self._rate_limiter = _get_rate_limiter(provider)
        self._backend = self._load_backend(provider, model)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(self, prompt: str, estimated_tokens: Optional[int] = None) -> str:
        """
        Send *prompt* to the LLM and return the completion text.

        Rate limiting is applied before the API call is made.

        Args:
            prompt:           The prompt string.
            estimated_tokens: Estimated token count for rate-limit accounting.
                              Defaults to ``len(prompt) // 4`` (rough approximation).

        Returns:
            The completion text.

        Raises:
            SummarizerError: On API errors or rate-limit timeout.
        """
        if estimated_tokens is None:
            estimated_tokens = max(1, len(prompt) // 4)

        if self._rate_limiter is not None:
            acquired = self._rate_limiter.acquire(
                estimated_tokens=estimated_tokens,
                timeout=300,  # 5-minute hard timeout
            )
            if not acquired:
                raise SummarizerError(
                    f"Rate limit timeout: could not acquire quota for provider '{self.provider}' "
                    "within 5 minutes."
                )
            logger.debug(
                "Rate limit slot acquired for %s (est. %d tokens)",
                self.provider,
                estimated_tokens,
            )

        return self._call_backend(prompt)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_backend(self, prompt: str) -> str:
        """Delegate to the provider backend."""
        try:
            return self._backend.complete(prompt)
        except SummarizerError:
            raise
        except Exception as exc:
            raise SummarizerError(
                f"LLM backend error ({self.provider}/{self.model}): {exc}"
            ) from exc

    def _load_backend(self, provider: str, model: str) -> Any:
        """Dynamically load the correct provider backend."""
        provider_lower = provider.lower()

        try:
            if provider_lower == "openai":
                from .providers.openai import OpenAIBackend
                return OpenAIBackend(model=model)

            if provider_lower in ("anthropic", "claude"):
                from .providers.anthropic import AnthropicBackend
                return AnthropicBackend(model=model)

            if provider_lower in ("gemini", "google"):
                from .providers.gemini import GeminiBackend
                return GeminiBackend(model=model)

            if provider_lower == "ollama":
                from .providers.ollama import OllamaBackend
                return OllamaBackend(model=model)

            raise SummarizerError(
                f"Unknown provider '{provider}'. "
                "Supported: openai, anthropic, gemini, ollama."
            )

        except ImportError as exc:
            raise SummarizerError(
                f"Provider '{provider}' is not available. "
                f"Check that the required package is installed. Details: {exc}"
            ) from exc