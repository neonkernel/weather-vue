"""Top-level orchestration: takes an Article, returns a Summary."""

from __future__ import annotations

import logging
from typing import Optional

from .config import Config
from .exceptions import SummarizerError
from .llm.chunker import map_reduce_summarize
from .llm.client import SummarizerClient
from .llm.prompts import PromptBuilder, SummaryStyle
from .llm.token_utils import fits_in_context
from .models import Article, Summary

logger = logging.getLogger(__name__)


def summarize(
    article: Article,
    config: Optional[Config] = None,
    style: SummaryStyle = SummaryStyle.CONCISE,
    client: Optional[SummarizerClient] = None,
) -> Summary:
    """Summarize an article using the configured LLM.

    This function decides whether to use direct summarization (for articles
    that fit within the model's context window) or map-reduce chunked
    summarization (for longer articles).

    Args:
        article: The Article object to summarize.
        config: Optional Config object. Defaults to Config().
        style: The summary style to use.
        client: Optional pre-configured SummarizerClient. If not provided,
                one is created from config.

    Returns:
        A Summary dataclass containing the summary text and metadata.

    Raises:
        SummarizerError: If summarization fails.
    """
    if config is None:
        config = Config()

    if client is None:
        client = SummarizerClient(
            api_key=config.openai_api_key,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            max_retries=config.max_retries,
            base_url=getattr(config, "base_url", None),
        )

    prompt_builder = PromptBuilder(style=style)

    logger.info(
        "Starting summarization for article: '%s' (%d chars)",
        article.title or "Untitled",
        len(article.content),
    )

    try:
        content_fits = fits_in_context(
            article.content,
            model=config.model,
        )

        if content_fits:
            logger.info("Using direct summarization (content fits in context window).")
            summary_text, prompt_tokens, completion_tokens = _direct_summarize(
                article=article,
                client=client,
                prompt_builder=prompt_builder,
            )
            strategy = "direct"
        else:
            logger.info(
                "Content exceeds context window — using map-reduce summarization."
            )
            summary_text, prompt_tokens, completion_tokens = map_reduce_summarize(
                text=article.content,
                title=article.title or "",
                client=client,
                prompt_builder=prompt_builder,
                model=config.model,
            )
            strategy = "map_reduce"

        logger.info(
            "Summarization complete. Strategy: %s | Total tokens: %d",
            strategy,
            prompt_tokens + completion_tokens,
        )

        return Summary(
            article_title=article.title or "Untitled",
            summary=summary_text.strip(),
            model=config.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            strategy=strategy,
        )

    except Exception as exc:
        logger.error("Summarization failed: %s", exc, exc_info=True)
        raise SummarizerError(f"Failed to summarize article: {exc}") from exc


def _direct_summarize(
    article: Article,
    client: SummarizerClient,
    prompt_builder: PromptBuilder,
) -> tuple[str, int, int]:
    """Summarize an article directly (no chunking).

    Args:
        article: The Article to summarize.
        client: The SummarizerClient.
        prompt_builder: The PromptBuilder.

    Returns:
        Tuple of (summary_text, prompt_tokens, completion_tokens).
    """
    messages = prompt_builder.build_messages(
        content=article.content,
        title=article.title or "",
    )
    return client.complete(messages)