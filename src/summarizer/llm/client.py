"""SummarizerClient: wraps OpenAI client with retry logic and token logging."""

import logging
from typing import Optional, Any

import openai
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from ..config import Config
from .token_utils import estimate_cost

logger = logging.getLogger(__name__)

# Transient errors that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)


def _is_retryable(exc: BaseException) -> bool:
    """Check if an exception is retryable."""
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


class SummarizerClient:
    """Wraps OpenAI client with authentication, retry logic, and token logging.

    Args:
        config: Configuration object containing API key, model, etc.
        api_key: Optional API key override (takes precedence over config).
        base_url: Optional base URL override for compatible endpoints.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.config = config or Config()
        self.model = self.config.model
        self.temperature = self.config.temperature
        self.max_tokens = self.config.max_tokens

        # Build OpenAI client kwargs
        client_kwargs: dict[str, Any] = {}
        resolved_api_key = api_key or self.config.openai_api_key
        if resolved_api_key:
            client_kwargs["api_key"] = resolved_api_key
        if base_url or getattr(self.config, "base_url", None):
            client_kwargs["base_url"] = base_url or self.config.base_url

        self._client = OpenAI(**client_kwargs)
        logger.info(
            "SummarizerClient initialized with model='%s', temperature=%s, max_tokens=%s",
            self.model,
            self.temperature,
            self.max_tokens,
        )

    def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Make a completion request with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Optional model override.
            temperature: Optional temperature override.
            max_tokens: Optional max_tokens override.

        Returns:
            The completion text.

        Raises:
            openai.OpenAIError: If the API call fails after all retries.
        """
        resolved_model = model or self.model
        resolved_temperature = temperature if temperature is not None else self.temperature
        resolved_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        return self._complete_with_retry(
            messages=messages,
            model=resolved_model,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
        )

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _complete_with_retry(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Internal method that performs the actual API call with tenacity retry.

        Args:
            messages: List of message dicts.
            model: Model name.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            The completion text.
        """
        logger.debug(
            "Calling OpenAI API: model=%s, temperature=%s, max_tokens=%s, messages=%d",
            model,
            temperature,
            max_tokens,
            len(messages),
        )

        response = self._client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Extract usage information and log it
        usage = response.usage
        if usage:
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            cost = estimate_cost(prompt_tokens, completion_tokens, model)

            logger.info(
                "Token usage — prompt: %d, completion: %d, total: %d | estimated cost: $%.6f",
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost,
            )
        else:
            logger.warning("No usage information returned from API")

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("OpenAI returned an empty response")

        return content.strip()