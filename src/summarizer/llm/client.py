"""SummarizerClient: wraps openai.OpenAI with retry logic and token logging."""

import logging
import os
from typing import Any, Optional

import openai
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import SummarizerConfig
from .token_utils import count_tokens, estimate_cost

logger = logging.getLogger(__name__)

# Transient errors worth retrying
_RETRYABLE_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, _RETRYABLE_EXCEPTIONS)


class SummarizerClient:
    """
    Thin wrapper around openai.OpenAI that adds:

    * Retry logic (3 attempts, exponential back-off via tenacity).
    * Per-call token usage logging.
    * Cost estimation.

    Args:
        config: A SummarizerConfig instance.  If omitted a default config
                is constructed; the OpenAI API key is read from the
                ``OPENAI_API_KEY`` environment variable.
        api_key: Explicit API key (overrides config and env var).
        base_url: Optional custom base URL (for OpenAI-compatible endpoints).
    """

    def __init__(
        self,
        config: Optional[SummarizerConfig] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.config = config or SummarizerConfig()
        self.model: str = self.config.model
        self.temperature: float = self.config.temperature
        self.max_tokens: int = self.config.max_tokens

        resolved_key = api_key or self.config.api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "No OpenAI API key provided. Set the OPENAI_API_KEY environment "
                "variable or pass api_key= to SummarizerClient."
            )

        client_kwargs: dict[str, Any] = {"api_key": resolved_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        elif self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        self._client = openai.OpenAI(**client_kwargs)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, dict[str, int]]:
        """
        Call the chat completions endpoint with retry logic.

        Args:
            messages: List of message dicts (role/content) for the chat API.
            temperature: Override the client-level temperature.
            max_tokens: Override the client-level max_tokens.

        Returns:
            A tuple of (response_text, usage_dict) where usage_dict has keys
            ``prompt_tokens``, ``completion_tokens``, and ``total_tokens``.
        """
        return self._complete_with_retry(
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _complete_with_retry(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict[str, int]]:
        """Calls _call_api with tenacity retry logic applied at call-time."""

        @retry(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _inner() -> tuple[str, dict[str, int]]:
            return self._call_api(messages, temperature, max_tokens)

        return _inner()

    def _call_api(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict[str, int]]:
        """
        Make a single chat completions request and log token usage.

        Returns:
            (response_text, usage_dict)
        """
        logger.debug(
            "Calling %s (temp=%.2f, max_tokens=%d, messages=%d).",
            self.model,
            temperature,
            max_tokens,
            len(messages),
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response_text = (response.choices[0].message.content or "").strip()

        usage_dict: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        if response.usage:
            usage_dict["prompt_tokens"] = response.usage.prompt_tokens
            usage_dict["completion_tokens"] = response.usage.completion_tokens
            usage_dict["total_tokens"] = response.usage.total_tokens

        cost = estimate_cost(
            prompt_tokens=usage_dict["prompt_tokens"],
            completion_tokens=usage_dict["completion_tokens"],
            model=self.model,
        )

        logger.info(
            "Token usage — prompt: %d, completion: %d, total: %d | "
            "estimated cost: $%.6f (model: %s)",
            usage_dict["prompt_tokens"],
            usage_dict["completion_tokens"],
            usage_dict["total_tokens"],
            cost,
            self.model,
        )

        return response_text, usage_dict