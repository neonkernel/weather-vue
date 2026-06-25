"""SummarizerClient: wraps the OpenAI API with retry logic and token logging."""

import logging
import os
from typing import Any, Optional

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    RetryError,
)

from .token_utils import count_tokens, estimate_cost

logger = logging.getLogger(__name__)

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)


def _is_retryable(exception: BaseException) -> bool:
    """Check if an exception is retryable."""
    return isinstance(exception, RETRYABLE_EXCEPTIONS)


class SummarizerClient:
    """
    Wraps the OpenAI client for summarization tasks.

    Handles:
    - Authentication via API key
    - Model selection and configuration
    - API calls with retry logic (3 attempts, exponential backoff)
    - Token usage logging and cost estimation
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize the SummarizerClient.

        Args:
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
            model: Model to use for summarization.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens in the completion.
            base_url: Optional custom base URL for OpenAI-compatible endpoints.
            timeout: Request timeout in seconds.
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_api_key:
            raise ValueError(
                "OpenAI API key must be provided via the 'api_key' parameter "
                "or the OPENAI_API_KEY environment variable."
            )

        client_kwargs: dict[str, Any] = {
            "api_key": resolved_api_key,
            "timeout": timeout,
        }
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = openai.OpenAI(**client_kwargs)

        logger.info(
            f"SummarizerClient initialized: model={model}, temperature={temperature}, "
            f"max_tokens={max_tokens}"
        )

    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        """
        Send a chat completion request with retry logic.

        Args:
            messages: List of message dictionaries for the OpenAI API.

        Returns:
            A tuple of (response_text, usage_dict).
        """
        return self._complete_with_retry(messages)

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _complete_with_retry(self, messages: list[dict]) -> tuple[str, dict]:
        """
        Internal method that makes the API call (decorated with retry logic).

        Args:
            messages: List of message dictionaries.

        Returns:
            A tuple of (response_text, usage_dict).
        """
        logger.debug(
            f"Sending completion request: model={self.model}, "
            f"messages={len(messages)}, temperature={self.temperature}"
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        response_text = response.choices[0].message.content or ""

        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        # Log token usage and estimated cost
        estimated_cost = estimate_cost(
            usage["prompt_tokens"],
            usage["completion_tokens"],
            self.model,
        )

        logger.info(
            f"API call complete — model={self.model}, "
            f"prompt_tokens={usage['prompt_tokens']}, "
            f"completion_tokens={usage['completion_tokens']}, "
            f"total_tokens={usage['total_tokens']}, "
            f"estimated_cost=${estimated_cost:.6f}"
        )

        return response_text, usage

    def count_message_tokens(self, messages: list[dict]) -> int:
        """
        Estimate the token count for a list of messages.

        Args:
            messages: List of message dictionaries.

        Returns:
            Estimated token count.
        """
        total = 0
        for message in messages:
            # Add 4 tokens per message for role/formatting overhead
            total += 4
            total += count_tokens(message.get("content", ""), self.model)
            total += count_tokens(message.get("role", ""), self.model)
        # Add 2 tokens for reply priming
        total += 2
        return total