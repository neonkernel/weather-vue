"""SummarizerClient: wraps the OpenAI API with retry logic and token logging."""

import logging
import time
from typing import Optional

import openai
from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    RetryError,
)

from ..config import get_config
from .token_utils import estimate_cost

logger = logging.getLogger(__name__)

# Transient error types that warrant a retry
RETRYABLE_EXCEPTIONS = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)


def _is_retryable(exc: BaseException) -> bool:
    """Determine if an exception is worth retrying."""
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


class SummarizerClient:
    """Wraps the OpenAI client for summarization tasks.

    Handles authentication, model selection, API calls, and retry logic.

    Args:
        api_key: OpenAI API key. Falls back to config / OPENAI_API_KEY env var.
        model: Model name to use. Defaults to 'gpt-4o-mini'.
        temperature: Sampling temperature (0.0–2.0). Default 0.3 for consistency.
        max_tokens: Maximum tokens in the completion. Default 1024.
        base_url: Optional custom API base URL (for compatible endpoints).
        max_retries: Number of retry attempts for transient errors. Default 3.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        base_url: Optional[str] = None,
        max_retries: int = 3,
    ) -> None:
        config = get_config()

        resolved_api_key = api_key or config.openai_api_key
        resolved_base_url = base_url or config.openai_base_url

        client_kwargs = {"api_key": resolved_api_key}
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url

        self._client = OpenAI(**client_kwargs)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

        # Track cumulative usage
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cost_usd = 0.0
        self._call_count = 0

        logger.debug(
            "SummarizerClient initialized: model=%s, temperature=%.2f, max_tokens=%d",
            self.model,
            self.temperature,
            self.max_tokens,
        )

    def complete(self, messages: list[dict]) -> str:
        """Send messages to the OpenAI API and return the response text.

        Implements retry logic with exponential backoff for transient errors.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.

        Returns:
            The response text from the model.

        Raises:
            openai.AuthenticationError: If the API key is invalid.
            openai.BadRequestError: If the request is malformed.
            RetryError: If all retry attempts are exhausted.
        """
        return self._complete_with_retry(messages)

    def _complete_with_retry(self, messages: list[dict]) -> str:
        """Internal method with tenacity retry logic applied."""
        attempt = 0
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return self._make_api_call(messages)
            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    "Retryable API error on attempt %d/%d: %s. Retrying in %ds...",
                    attempt + 1,
                    self.max_retries,
                    type(e).__name__,
                    wait_time,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
            except (openai.AuthenticationError, openai.BadRequestError):
                # Don't retry these — they won't resolve with a retry
                raise

        logger.error(
            "All %d retry attempts exhausted. Last error: %s",
            self.max_retries,
            last_exception,
        )
        raise last_exception

    def _make_api_call(self, messages: list[dict]) -> str:
        """Make a single API call and log token usage.

        Args:
            messages: The messages to send.

        Returns:
            The response text.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Extract usage information
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        # Update cumulative counters
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self._call_count += 1

        call_cost = estimate_cost(prompt_tokens, completion_tokens, self.model)
        self._total_cost_usd += call_cost

        logger.info(
            "API call #%d — model=%s | prompt=%d tokens, completion=%d tokens, "
            "total=%d tokens | estimated cost=$%.6f",
            self._call_count,
            self.model,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            call_cost,
        )

        # Extract response text
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Received empty response content from API")

        return content.strip()

    @property
    def usage_stats(self) -> dict:
        """Return cumulative usage statistics."""
        return {
            "call_count": self._call_count,
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
            "total_cost_usd": self._total_cost_usd,
        }

    def log_usage_summary(self) -> None:
        """Log a summary of cumulative token usage and cost."""
        stats = self.usage_stats
        logger.info(
            "Usage summary: %d calls | %d prompt tokens | %d completion tokens | "
            "%d total tokens | $%.6f estimated cost",
            stats["call_count"],
            stats["total_prompt_tokens"],
            stats["total_completion_tokens"],
            stats["total_tokens"],
            stats["total_cost_usd"],
        )