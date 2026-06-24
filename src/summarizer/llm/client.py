"""SummarizerClient: wraps openai.OpenAI with retry logic and token logging."""

from __future__ import annotations

import logging
import os
from typing import Optional

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .token_utils import DEFAULT_MODEL, estimate_cost

logger = logging.getLogger(__name__)

# Transient errors that should be retried
_RETRYABLE_ERRORS = (
    APIConnectionError,
    APITimeoutError,
)

# 429 (rate limit) and 5xx server errors
def _is_retryable_status_error(exc: BaseException) -> bool:
    if isinstance(exc, APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, _RETRYABLE_ERRORS) or _is_retryable_status_error(exc)


class SummarizerClient:
    """Wraps the OpenAI client with retry logic and usage logging.

    Args:
        api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
        model: Model to use for completions.
        temperature: Sampling temperature (0.0–2.0).
        max_tokens: Maximum tokens in the completion.
        max_retries: Number of retry attempts for transient errors.
        base_url: Optional custom base URL (for compatible endpoints).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        max_retries: int = 3,
        base_url: Optional[str] = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

        client_kwargs: dict = {
            "api_key": api_key or os.environ.get("OPENAI_API_KEY"),
        }
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = OpenAI(**client_kwargs)
        logger.info(
            "SummarizerClient initialized: model=%s, temperature=%s, max_tokens=%d",
            self.model,
            self.temperature,
            self.max_tokens,
        )

    def _make_api_call(
        self, messages: list[dict[str, str]]
    ) -> tuple[str, int, int]:
        """Make a single API call without retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens).
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        content = response.choices[0].message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0

        return content, prompt_tokens, completion_tokens

    def complete(
        self, messages: list[dict[str, str]]
    ) -> tuple[str, int, int]:
        """Call the OpenAI API with retry logic and usage logging.

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            Tuple of (response_text, prompt_tokens, completion_tokens).

        Raises:
            Exception: After all retries are exhausted.
        """
        attempt_count = 0

        @retry(
            retry=retry_if_exception_type(
                (APIConnectionError, APITimeoutError, APIStatusError)
            ),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            stop=stop_after_attempt(self.max_retries),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _call_with_retry() -> tuple[str, int, int]:
            nonlocal attempt_count
            attempt_count += 1

            # For status errors, only retry on 429 and 5xx
            try:
                return self._make_api_call(messages)
            except APIStatusError as exc:
                if exc.status_code == 429 or exc.status_code >= 500:
                    logger.warning(
                        "Retryable API status error (attempt %d): %s %s",
                        attempt_count,
                        exc.status_code,
                        exc.message,
                    )
                    raise
                # 4xx errors that are not 429 should not be retried
                raise

        result = _call_with_retry()
        content, prompt_tokens, completion_tokens = result

        self._log_usage(prompt_tokens, completion_tokens)
        return content, prompt_tokens, completion_tokens

    def _log_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Log token usage and estimated cost."""
        total_tokens = prompt_tokens + completion_tokens
        cost = estimate_cost(prompt_tokens, completion_tokens, self.model)
        logger.info(
            "Token usage — prompt: %d, completion: %d, total: %d | "
            "Estimated cost: $%.6f (model: %s)",
            prompt_tokens,
            completion_tokens,
            total_tokens,
            cost,
            self.model,
        )