"""SummarizerClient: wraps openai.OpenAI with retry logic and prompt building."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from .prompts import PromptBuilder, SummaryStyle
from .token_utils import estimate_cost, fits_in_context
from .chunker import map_reduce_summarize

logger = logging.getLogger(__name__)

# Transient errors that warrant a retry
_RETRYABLE_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 1_024


@dataclass
class SummarizerClient:
    """High-level client for producing text summaries via the OpenAI API."""

    api_key: str | None = None
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    style: SummaryStyle = "concise"
    base_url: str | None = None  # Override for compatible endpoints
    extra_instructions: str = ""

    # Set after __post_init__
    _client: openai.OpenAI = field(init=False, repr=False)
    prompt_builder: PromptBuilder = field(init=False, repr=False)

    def __post_init__(self) -> None:
        client_kwargs: dict[str, Any] = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self._client = openai.OpenAI(**client_kwargs)
        self.prompt_builder = PromptBuilder(
            style=self.style,
            extra_instructions=self.extra_instructions,
        )

    # ------------------------------------------------------------------
    # Internal API call (with retry)
    # ------------------------------------------------------------------

    def _call_api(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, int]]:
        """Call the OpenAI chat completions endpoint with retry logic.

        Returns:
            (content_text, usage_dict)
        """
        return self._call_api_with_retry(messages)

    @property
    def _retry_decorator(self):
        return retry(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    def _call_api_with_retry(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, int]]:
        """Wrapped API call with exponential backoff retry."""

        @retry(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _inner() -> tuple[str, dict[str, int]]:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
            cost = estimate_cost(usage["prompt_tokens"], usage["completion_tokens"], self.model)
            logger.info(
                "API call complete — model=%s prompt_tokens=%d completion_tokens=%d "
                "total_tokens=%d estimated_cost=$%.6f",
                self.model,
                usage["prompt_tokens"],
                usage["completion_tokens"],
                usage["total_tokens"],
                cost,
            )
            return content.strip(), usage

        return _inner()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def summarize(self, text: str) -> tuple[str, dict[str, int]]:
        """Summarize *text*, using chunking if it exceeds the context window.

        Returns:
            (summary_text, usage_dict)
            Note: for chunked summarization the usage dict reflects only the
            final (reduce) call; individual chunk usages are logged separately.
        """
        if fits_in_context(text, self.model):
            messages = self.prompt_builder.build_messages(text)
            return self._call_api(messages)
        else:
            logger.info(
                "Text exceeds context window for model '%s'; switching to map-reduce.",
                self.model,
            )
            summary = map_reduce_summarize(text, client=self, style=self.style)
            # Return empty usage for the overall call (individual calls are logged)
            return summary, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}