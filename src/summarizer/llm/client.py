"""LLM client with integrated rate limiting."""

from __future__ import annotations

import logging
from typing import Optional

from ..rate_limiter import TokenBucket, get_rate_limiter

logger = logging.getLogger(__name__)

# Registry so one bucket is shared across all client instances per provider
_rate_limiters: dict[str, TokenBucket] = {}


def _get_or_create_limiter(provider: str) -> TokenBucket:
    if provider not in _rate_limiters:
        _rate_limiters[provider] = get_rate_limiter(provider)
    return _rate_limiters[provider]


class LLMClient:
    """
    Thin wrapper around provider-specific completion APIs.

    Integrates a TokenBucket rate limiter that is shared across all instances
    for the same provider, so concurrent callers obey the same limits.
    """

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        rate_limiter: Optional[TokenBucket] = None,
    ) -> None:
        self.provider = provider.lower()
        self.model = model or self._default_model()
        self._rate_limiter = rate_limiter or _get_or_create_limiter(self.provider)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _default_model(self) -> str:
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
            "ollama": "llama3",
        }
        return defaults.get(self.provider, "gpt-4o-mini")

    def _call_provider(self, prompt: str) -> str:
        """Route to the correct provider backend. Override in tests."""
        if self.provider == "openai":
            return self._call_openai(prompt)
        if self.provider == "anthropic":
            return self._call_anthropic(prompt)
        if self.provider == "ollama":
            return self._call_ollama(prompt)
        raise ValueError(f"Unknown provider: {self.provider!r}")

    def _call_openai(self, prompt: str) -> str:
        try:
            import openai  # type: ignore

            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except ImportError as exc:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai"
            ) from exc

    def _call_anthropic(self, prompt: str) -> str:
        try:
            import anthropic  # type: ignore

            client = anthropic.Anthropic()
            message = client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

    def _call_ollama(self, prompt: str) -> str:
        try:
            import requests  # type: ignore

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except ImportError as exc:
            raise RuntimeError(
                "requests package not installed. Run: pip install requests"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(self, prompt: str, estimated_tokens: int = 0) -> str:
        """
        Send a completion request, honoring rate limits.

        Parameters
        ----------
        prompt:
            The full prompt string to send to the model.
        estimated_tokens:
            Rough token count for the request+response, used by the
            token-per-minute bucket.  Pass 0 to skip TPM limiting.
        """
        logger.debug(
            "Acquiring rate-limit slot (provider=%s, est_tokens=%d)",
            self.provider,
            estimated_tokens,
        )
        self._rate_limiter.acquire(estimated_tokens=estimated_tokens)
        logger.debug("Calling %s/%s", self.provider, self.model)
        result = self._call_provider(prompt)
        logger.debug("Provider returned %d chars", len(result))
        return result