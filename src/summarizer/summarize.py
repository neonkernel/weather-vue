"""Top-level orchestration for article summarization."""

import logging
from typing import Optional

from .config import Config
from .exceptions import SummarizerError
from .llm.client import SummarizerClient
from .llm.chunker import MapReduceSummarizer, TextChunker
from .llm.prompts import PromptBuilder
from .llm.token_utils import fits_in_context, RESERVED_TOKENS
from .models import Article, Summary

logger = logging.getLogger(__name__)


def summarize(
    article: Article,
    style: str = "concise",
    config: Optional[Config] = None,
    client: Optional[SummarizerClient] = None,
) -> Summary:
    """Summarize an article, automatically choosing direct or chunked strategy.

    For articles that fit within the model's context window, a direct single-pass
    summarization is used. For longer articles, a map-reduce chunking strategy
    is applied: the article is split into overlapping chunks, each is summarized
    independently, and then the chunk summaries are merged into a final summary.

    Args:
        article: The Article to summarize.
        style: Summary style ('concise', 'detailed', 'bullet', 'executive').
        config: Optional Config object. Defaults to Config().
        client: Optional SummarizerClient (useful for testing/injection).

    Returns:
        A Summary dataclass containing the summary text and metadata.

    Raises:
        SummarizerError: If summarization fails.
    """
    cfg = config or Config()

    if client is None:
        client = SummarizerClient(config=cfg)

    prompt_builder = PromptBuilder(style=style)

    logger.info(
        "Starting summarization of article '%s' (style='%s', model='%s')",
        article.title or "(untitled)",
        style,
        client.model,
    )

    try:
        # Determine if the article fits in the context window
        if fits_in_context(article.text, model=client.model, reserved_tokens=RESERVED_TOKENS):
            logger.info("Article fits in context window — using direct summarization")
            summary_text, was_chunked, chunk_count = _direct_summarize(
                article=article,
                client=client,
                prompt_builder=prompt_builder,
            )
        else:
            logger.info(
                "Article exceeds context window — using map-reduce chunked summarization"
            )
            summary_text, was_chunked, chunk_count = _chunked_summarize(
                article=article,
                client=client,
                prompt_builder=prompt_builder,
                config=cfg,
            )

        summary = Summary(
            text=summary_text,
            article_title=article.title,
            style=style,
            model=client.model,
            was_chunked=was_chunked,
            chunk_count=chunk_count,
        )

        logger.info(
            "Summarization complete: %d chars, chunked=%s, chunks=%d",
            len(summary_text),
            was_chunked,
            chunk_count,
        )
        return summary

    except Exception as exc:
        logger.error("Summarization failed: %s", exc, exc_info=True)
        if isinstance(exc, SummarizerError):
            raise
        raise SummarizerError(f"Summarization failed: {exc}") from exc


def _direct_summarize(
    article: Article,
    client: SummarizerClient,
    prompt_builder: PromptBuilder,
) -> tuple[str, bool, int]:
    """Perform direct single-pass summarization.

    Args:
        article: The article to summarize.
        client: The SummarizerClient.
        prompt_builder: The PromptBuilder.

    Returns:
        Tuple of (summary_text, was_chunked=False, chunk_count=1).
    """
    messages = prompt_builder.build_direct_messages(
        article_text=article.text,
        title=article.title,
    )
    summary_text = client.complete(messages)
    return summary_text, False, 1


def _chunked_summarize(
    article: Article,
    client: SummarizerClient,
    prompt_builder: PromptBuilder,
    config: Config,
) -> tuple[str, bool, int]:
    """Perform map-reduce chunked summarization.

    Args:
        article: The article to summarize.
        client: The SummarizerClient.
        prompt_builder: The PromptBuilder.
        config: The configuration.

    Returns:
        Tuple of (summary_text, was_chunked=True, chunk_count).
    """
    chunker = TextChunker(
        model=client.model,
        max_chunk_tokens=config.max_chunk_tokens,
        overlap_tokens=config.overlap_tokens,
    )
    map_reduce = MapReduceSummarizer(
        client=client,
        prompt_builder=prompt_builder,
        chunker=chunker,
    )

    # Pre-calculate chunk count for metadata
    chunks = chunker.split(article.text)
    chunk_count = len(chunks)

    summary_text = map_reduce.summarize(
        text=article.text,
        title=article.title,
    )
    return summary_text, True, chunk_count