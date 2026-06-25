"""Top-level orchestration: Article → Summary."""

import logging
from datetime import datetime, timezone
from typing import Optional

from .config import SummarizerConfig
from .exceptions import SummarizationError
from .llm.chunker import MapReduceSummarizer, TextChunker
from .llm.client import SummarizerClient
from .llm.prompts import PromptBuilder, SummaryStyle
from .llm.token_utils import fits_in_context
from .models import Article, Summary

logger = logging.getLogger(__name__)


def summarize(
    article: Article,
    *,
    config: Optional[SummarizerConfig] = None,
    style: SummaryStyle = SummaryStyle.CONCISE,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Summary:
    """
    Summarize *article* using the configured LLM.

    This function decides whether to use a single-pass summarization or
    the map-reduce chunked pipeline based on whether the article text
    fits within the model's context window.

    Args:
        article: The Article to summarize.
        config: Optional SummarizerConfig.  Defaults are used if omitted.
        style: The desired SummaryStyle.
        api_key: Explicit OpenAI API key (overrides config/env var).
        base_url: Optional custom base URL for OpenAI-compatible endpoints.

    Returns:
        A Summary dataclass populated with the result.

    Raises:
        SummarizationError: If summarization fails after all retries.
    """
    cfg = config or SummarizerConfig()

    logger.info(
        "Starting summarization for article '%s' (style=%s, model=%s).",
        article.title or "<untitled>",
        style.value,
        cfg.model,
    )

    try:
        client = SummarizerClient(config=cfg, api_key=api_key, base_url=base_url)
        prompt_builder = PromptBuilder(style=style)

        text = article.text.strip()
        if not text:
            raise SummarizationError("Article text is empty.")

        if fits_in_context(text, model=cfg.model, reserved_tokens=cfg.max_tokens + 500):
            # --- Single-pass ---
            logger.info("Article fits in context window; using single-pass summarization.")
            messages = prompt_builder.build(text)
            summary_text, usage = client.complete(messages)
            strategy = "single-pass"
        else:
            # --- Map-reduce ---
            logger.info(
                "Article exceeds context window; using map-reduce chunked summarization."
            )
            chunker = TextChunker(
                model=cfg.model,
                chunk_tokens=cfg.chunk_tokens,
                overlap_tokens=cfg.overlap_tokens,
            )
            map_reduce = MapReduceSummarizer(
                client=client,
                prompt_builder=prompt_builder,
                chunker=chunker,
            )
            summary_text, usage = map_reduce.summarize(text)
            strategy = "map-reduce"

    except SummarizationError:
        raise
    except Exception as exc:
        logger.exception("Summarization failed: %s", exc)
        raise SummarizationError(f"Summarization failed: {exc}") from exc

    logger.info(
        "Summarization complete (strategy=%s). Total tokens: %d.",
        strategy,
        usage.get("total_tokens", 0),
    )

    return Summary(
        article_title=article.title or "",
        article_url=article.url or "",
        summary_text=summary_text,
        model=cfg.model,
        style=style.value,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        strategy=strategy,
        created_at=datetime.now(tz=timezone.utc),
    )