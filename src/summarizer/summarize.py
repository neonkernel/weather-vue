"""Top-level orchestration for article summarization."""

import logging
from typing import Optional

from .config import get_config
from .exceptions import SummarizationError
from .llm.client import SummarizerClient
from .llm.chunker import TextChunker, run_map_reduce
from .llm.prompts import PromptBuilder
from .llm.token_utils import fits_in_context, count_tokens
from .models import Article, Summary

logger = logging.getLogger(__name__)


def summarize(
    article: Article,
    client: Optional[SummarizerClient] = None,
    style: str = "concise",
    max_summary_words: Optional[int] = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 1024,
    chunk_overlap: int = 100,
) -> Summary:
    """Summarize an article using the LLM.

    Automatically decides between direct summarization and chunked (map-reduce)
    summarization based on the article's token count.

    Args:
        article: The Article object to summarize.
        client: Optional pre-configured SummarizerClient. If not provided, one
                will be created using the application config.
        style: Summary style — 'concise', 'detailed', 'bullet', or 'executive'.
        max_summary_words: Optional word limit for the summary.
        model: The OpenAI model to use.
        temperature: Sampling temperature.
        max_tokens: Maximum completion tokens.
        chunk_overlap: Token overlap between chunks in map-reduce mode.

    Returns:
        A Summary dataclass with the generated summary text and metadata.

    Raises:
        SummarizationError: If the summarization fails.
    """
    if client is None:
        client = SummarizerClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    prompt_builder = PromptBuilder(
        style=style,
        max_summary_words=max_summary_words,
    )

    article_text = article.content
    article_title = getattr(article, "title", None)

    token_count = count_tokens(article_text, model)
    logger.info(
        "Starting summarization for article '%s' (%d tokens)",
        article_title or "Untitled",
        token_count,
    )

    try:
        if fits_in_context(article_text, model):
            logger.info("Using direct summarization (article fits in context window)")
            summary_text = _direct_summarize(
                article_text=article_text,
                article_title=article_title,
                client=client,
                prompt_builder=prompt_builder,
            )
            method = "direct"
        else:
            logger.info("Using map-reduce summarization (article exceeds context window)")
            summary_text = _chunked_summarize(
                article_text=article_text,
                article_title=article_title,
                client=client,
                prompt_builder=prompt_builder,
                model=model,
                chunk_overlap=chunk_overlap,
            )
            method = "map_reduce"

    except Exception as e:
        logger.error("Summarization failed: %s", e)
        raise SummarizationError(f"Failed to summarize article: {e}") from e

    client.log_usage_summary()

    stats = client.usage_stats

    summary = Summary(
        article_title=article_title,
        summary_text=summary_text,
        model=model,
        style=style,
        method=method,
        input_tokens=stats["total_prompt_tokens"],
        output_tokens=stats["total_completion_tokens"],
        estimated_cost_usd=stats["total_cost_usd"],
    )

    logger.info(
        "Summarization complete: method=%s, summary_length=%d chars",
        method,
        len(summary_text),
    )

    return summary


def _direct_summarize(
    article_text: str,
    article_title: Optional[str],
    client: SummarizerClient,
    prompt_builder: PromptBuilder,
) -> str:
    """Summarize the full article text in a single API call.

    Args:
        article_text: The article text.
        article_title: Optional title.
        client: The SummarizerClient.
        prompt_builder: The PromptBuilder.

    Returns:
        The summary text.
    """
    prompt = prompt_builder.build(article_text, title=article_title)
    messages = prompt.to_openai_messages()
    return client.complete(messages)


def _chunked_summarize(
    article_text: str,
    article_title: Optional[str],
    client: SummarizerClient,
    prompt_builder: PromptBuilder,
    model: str,
    chunk_overlap: int,
) -> str:
    """Summarize a long article using map-reduce chunking.

    Args:
        article_text: The full article text.
        article_title: Optional title.
        client: The SummarizerClient.
        prompt_builder: The PromptBuilder.
        model: The model name for token counting.
        chunk_overlap: Token overlap between chunks.

    Returns:
        The final combined summary.
    """
    system_prompt = prompt_builder.build_system_prompt()

    def summarize_fn(
        text: str,
        title: Optional[str],
        is_chunk: bool,
        chunk_index: int,
        total_chunks: int,
        is_reduce: bool = False,
        chunk_summaries: Optional[list[str]] = None,
    ) -> str:
        if is_reduce and chunk_summaries is not None:
            user_prompt = prompt_builder.build_reduce_user_prompt(
                chunk_summaries=chunk_summaries,
                title=title,
            )
        elif is_chunk:
            user_prompt = prompt_builder.build_chunk_user_prompt(
                chunk_text=text,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
            )
        else:
            user_prompt = prompt_builder.build_user_prompt(text, title=title)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return client.complete(messages)

    return run_map_reduce(
        text=article_text,
        summarize_fn=summarize_fn,
        model=model,
        overlap=chunk_overlap,
        title=article_title,
    )