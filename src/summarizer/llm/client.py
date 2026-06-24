"""SummarizerClient: wraps openai.OpenAI with retry logic and token logging."""

from __future__ import annotations

import logging
from typing import List

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.summarizer.config import Config
from src.summarizer.llm.prompts import Message, PromptBuilder, SummaryStyle
from src.summarizer.llm.chunker import split_into_chunks
from src.summarizer.llm.token_utils import estimate_cost, count_tokens
from src.summarizer.models import Summary

logger = logging.getLogger(__name__)

# Transient errors that should trigger a retry
_RETRYABLE_EXCEPTIONS = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)


def _build_retry_decorator():
    return retry(
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class SummarizerClient:
    """Wraps the OpenAI chat completions API for article summarization.

    Parameters
    ----------
    config:
        Application configuration (carries API key, model, temperature, etc.).
    style:
        Summary style to use (concise, detailed, bullet_points, executive).
    """

    def __init__(
        self,
        config: Config | None = None,
        style: SummaryStyle = SummaryStyle.CONCISE,
    ) -> None:
        self.config = config or Config()
        self.style = style
        self.prompt_builder = PromptBuilder(style=style)
        self._client = openai.OpenAI(
            api_key=self.config.openai_api_key,
            base_url=getattr(self.config, "openai_base_url", None) or "https://api.openai.com/v1",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summarize(self, article_text: str, title: str = "") -> Summary:
        """Summarize *article_text*, choosing direct or chunked strategy.

        Parameters
        ----------
        article_text:
            The raw text of the article.
        title:
            Optional article title used in the returned Summary.

        Returns
        -------
        Summary
            Populated Summary dataclass.
        """
        from src.summarizer.llm.token_utils import fits_in_context

        model = self.config.model
        # Reserve tokens for prompts + completion
        reserved = 2_000 + self.config.max_tokens

        if fits_in_context(article_text, model=model, reserved_tokens=reserved):
            logger.info("Article fits in context window; using direct summarization.")
            return self._direct_summarize(article_text, title=title)
        else:
            logger.info("Article exceeds context window; using chunked (map-reduce) summarization.")
            return self._chunked_summarize(article_text, title=title)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _direct_summarize(self, article_text: str, title: str = "") -> Summary:
        """Single-call summarization for articles that fit in context."""
        messages = self.prompt_builder.build_direct_messages(article_text)
        summary_text, usage = self._call_api(messages)
        return Summary(
            title=title,
            summary=summary_text,
            model=self.config.model,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
            estimated_cost=estimate_cost(
                usage["prompt_tokens"],
                usage["completion_tokens"],
                self.config.model,
            ),
        )

    def _chunked_summarize(self, article_text: str, title: str = "") -> Summary:
        """Map-reduce summarization for long articles."""
        model = self.config.model
        chunks = split_into_chunks(article_text, model=model)
        total_chunks = len(chunks)
        logger.info("Processing %d chunks for map-reduce summarization.", total_chunks)

        total_prompt_tokens = 0
        total_completion_tokens = 0
        partial_summaries: list[str] = []

        # --- MAP step: summarize each chunk independently ---
        for chunk in chunks:
            messages = self.prompt_builder.build_chunk_messages(
                chunk_text=chunk.text,
                chunk_index=chunk.index,
                total_chunks=chunk.total,
            )
            chunk_summary, usage = self._call_api(messages)
            partial_summaries.append(chunk_summary)
            total_prompt_tokens += usage["prompt_tokens"]
            total_completion_tokens += usage["completion_tokens"]
            logger.debug("Chunk %d/%d summarized.", chunk.index, chunk.total)

        # --- REDUCE step: combine partial summaries ---
        reduce_messages = self.prompt_builder.build_reduce_messages(partial_summaries)
        final_summary, reduce_usage = self._call_api(reduce_messages)
        total_prompt_tokens += reduce_usage["prompt_tokens"]
        total_completion_tokens += reduce_usage["completion_tokens"]

        total_tokens = total_prompt_tokens + total_completion_tokens
        cost = estimate_cost(total_prompt_tokens, total_completion_tokens, model)

        return Summary(
            title=title,
            summary=final_summary,
            model=model,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=cost,
        )

    @_build_retry_decorator()
    def _call_api(self, messages: List[Message]) -> tuple[str, dict]:
        """Make a single call to the OpenAI chat completions endpoint.

        Returns
        -------
        tuple[str, dict]
            The response text and a dict with token usage counts.
        """
        model = self.config.model
        response = self._client.chat.completions.create(
            model=model,
            messages=[m.to_dict() for m in messages],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        choice = response.choices[0]
        summary_text = (choice.message.content or "").strip()

        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        cost = estimate_cost(usage["prompt_tokens"], usage["completion_tokens"], model)
        logger.info(
            "API call complete — model=%s prompt_tokens=%d completion_tokens=%d "
            "total_tokens=%d estimated_cost=$%.6f",
            model,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
            cost,
        )

        return summary_text, usage