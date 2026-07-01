"""
LLM client that wraps provider-specific completion calls with rate limiting.
"""

import logging
from typing import Optional

from summarizer.rate_limiter import RateLimiter, get_rate_limiter

logger = logging.getLogger(__name__)

# Rough estimate: average tokens per character in English text
_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    """Rough token count estimate from character count."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


class LLMClient:
    """
    A unified LLM client that delegates to a provider-specific backend
    and applies rate limiting around each API call.
    """

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.last_tokens_used: Optional[int] = None
        self._rate_limiter = rate_limiter or get_rate_limiter(provider)
        self._backend = self._load_backend(provider, model)

    def _load_backend(self, provider: str, model: Optional[str]):
        """Load the provider-specific backend."""
        try:
            from summarizer.llm import providers
            return providers.get_provider(provider, model)
        except Exception as exc:
            logger.error("Failed to load backend for provider %s: %s", provider, exc)
            raise

    def summarize(
        self,
        text: str,
        style: str = "concise",
        title: Optional[str] = None,
        is_combination: bool = False,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Generate a summary for the given text using the configured LLM.

        Args:
            text: The text to summarize.
            style: Summary style (concise, detailed, bullet, eli5).
            title: Optional article title for context.
            is_combination: Whether this is a combination of chunk summaries.
            timeout: Max seconds to wait for rate limit. None = wait forever.

        Returns:
            The summary text as a string.
        """
        prompt = self._build_prompt(text=text, style=style, title=title, is_combination=is_combination)
        estimated_tokens = _estimate_tokens(prompt)

        # Apply rate limiting before the API call
        logger.debug(
            "Acquiring rate limit slot for %s (estimated %d tokens)",
            self.provider, estimated_tokens
        )
        acquired = self._rate_limiter.acquire(
            estimated_tokens=estimated_tokens,
            timeout=timeout,
        )
        if not acquired:
            raise TimeoutError(
                f"Rate limit timeout waiting for provider '{self.provider}'"
            )

        # Make the API call
        try:
            response = self._backend.complete(prompt)
            result_text = self._extract_text(response)
            actual_tokens = self._extract_tokens(response)

            # Adjust token bucket for actual vs estimated usage
            self._rate_limiter.record_actual_tokens(
                actual_tokens=actual_tokens or estimated_tokens,
                estimated_tokens=estimated_tokens,
            )

            self.last_tokens_used = actual_tokens
            logger.debug(
                "LLM call complete: provider=%s, tokens=%s",
                self.provider, actual_tokens
            )
            return result_text

        except Exception as exc:
            logger.error("LLM call failed for provider %s: %s", self.provider, exc)
            raise

    def complete(self, prompt: str, timeout: Optional[float] = None) -> str:
        """
        Low-level completion method with rate limiting.
        Use `summarize()` for higher-level access.
        """
        estimated_tokens = _estimate_tokens(prompt)

        acquired = self._rate_limiter.acquire(
            estimated_tokens=estimated_tokens,
            timeout=timeout,
        )
        if not acquired:
            raise TimeoutError(
                f"Rate limit timeout waiting for provider '{self.provider}'"
            )

        try:
            response = self._backend.complete(prompt)
            result_text = self._extract_text(response)
            actual_tokens = self._extract_tokens(response)

            self._rate_limiter.record_actual_tokens(
                actual_tokens=actual_tokens or estimated_tokens,
                estimated_tokens=estimated_tokens,
            )
            self.last_tokens_used = actual_tokens
            return result_text
        except Exception as exc:
            logger.error("LLM complete() failed for provider %s: %s", self.provider, exc)
            raise

    def _build_prompt(
        self,
        text: str,
        style: str,
        title: Optional[str] = None,
        is_combination: bool = False,
    ) -> str:
        """Build a summarization prompt."""
        from summarizer.styles import get_style_instruction

        style_instruction = get_style_instruction(style)
        title_line = f'Title: "{title}"\n\n' if title else ""

        if is_combination:
            return (
                f"You have been given several partial summaries of an article. "
                f"Combine them into a single, coherent summary.\n"
                f"{title_line}"
                f"{style_instruction}\n\n"
                f"Partial summaries:\n{text}"
            )

        return (
            f"Please summarize the following article.\n"
            f"{title_line}"
            f"{style_instruction}\n\n"
            f"Article:\n{text}"
        )

    def _extract_text(self, response) -> str:
        """Extract the text content from a provider response."""
        if isinstance(response, str):
            return response
        # Handle dict-like response
        if isinstance(response, dict):
            # OpenAI-style
            try:
                return response["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                pass
            # Generic fallback
            for key in ("text", "content", "output", "result"):
                if key in response:
                    return str(response[key])
        # Fallback: stringify
        return str(response)

    def _extract_tokens(self, response) -> Optional[int]:
        """Extract token usage from a provider response."""
        if isinstance(response, dict):
            # OpenAI-style
            usage = response.get("usage", {})
            if usage:
                return usage.get("total_tokens") or usage.get("completion_tokens")
            # Anthropic-style
            if "input_tokens" in response or "output_tokens" in response:
                return (response.get("input_tokens", 0) or 0) + (response.get("output_tokens", 0) or 0)
        return None