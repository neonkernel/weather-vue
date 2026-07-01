"""
Core summarization logic.
Orchestrates fetching, chunking, LLM calls, and caching.
"""

import logging
from typing import Optional

from summarizer.cache import SummaryCache
from summarizer.models import Summary

logger = logging.getLogger(__name__)


def summarize_url(
    url: str,
    style: str = "concise",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    cache: Optional[SummaryCache] = None,
) -> Summary:
    """
    Summarize an article at the given URL.

    Pipeline:
    1. Check cache (if enabled)
    2. Fetch and parse the article
    3. Chunk the content
    4. Call LLM (with rate limiting)
    5. Store result in cache
    6. Return Summary

    Args:
        url: The URL of the article to summarize.
        style: Summary style (concise, detailed, bullet, eli5).
        provider: LLM provider override.
        model: Model override.
        cache: SummaryCache instance. Pass None to disable caching.

    Returns:
        A Summary dataclass instance.
    """
    from summarizer.config import get_config
    from summarizer.ingestion import fetch_and_parse
    from summarizer.llm.client import LLMClient

    config = get_config()
    effective_provider = provider or config.provider
    effective_model = model or config.model

    # --- Step 1: Cache lookup ---
    if cache is not None:
        cached_summary = cache.get(
            url=url,
            style=style,
            provider=effective_provider,
            model=effective_model,
        )
        if cached_summary is not None:
            logger.info("Returning cached summary for %s", url)
            # Mark as cached for display
            try:
                object.__setattr__(cached_summary, "cached", True)
            except (TypeError, AttributeError):
                pass
            return cached_summary

    # --- Step 2: Fetch and parse ---
    logger.info("Fetching article: %s", url)
    article = fetch_and_parse(url)
    logger.debug("Fetched %d chars from %s", len(article.content), url)

    # --- Step 3: Chunk content ---
    chunks = _chunk_content(article.content, max_chunk_chars=config.max_chunk_chars)
    logger.debug("Split into %d chunk(s)", len(chunks))

    # --- Step 4: LLM call(s) ---
    client = LLMClient(provider=effective_provider, model=effective_model)

    if len(chunks) == 1:
        summary_text = client.summarize(
            text=chunks[0],
            style=style,
            title=article.title,
        )
        tokens_used = getattr(client, "last_tokens_used", None)
    else:
        summary_text, tokens_used = _summarize_chunks(
            client=client,
            chunks=chunks,
            style=style,
            title=article.title,
        )

    # --- Step 5: Build Summary object ---
    summary = Summary(
        url=url,
        title=article.title,
        text=summary_text,
        style=style,
        provider=effective_provider,
        model=effective_model,
        tokens_used=tokens_used,
        cached=False,
    )

    # --- Step 6: Store in cache ---
    if cache is not None:
        stored = cache.set(
            url=url,
            style=style,
            provider=effective_provider,
            model=effective_model,
            summary=summary,
        )
        if stored:
            logger.debug("Summary cached for %s", url)

    return summary


def _chunk_content(content: str, max_chunk_chars: int = 12_000) -> list[str]:
    """
    Split content into chunks of at most `max_chunk_chars` characters,
    attempting to break on paragraph boundaries.
    """
    if len(content) <= max_chunk_chars:
        return [content]

    chunks = []
    paragraphs = content.split("\n\n")
    current_chunk: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len + 2 > max_chunk_chars and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_len = 0

        # If a single paragraph exceeds the limit, hard-split it
        if para_len > max_chunk_chars:
            for i in range(0, para_len, max_chunk_chars):
                chunks.append(para[i : i + max_chunk_chars])
        else:
            current_chunk.append(para)
            current_len += para_len + 2  # +2 for '\n\n'

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return [c for c in chunks if c.strip()]


def _summarize_chunks(
    client,
    chunks: list[str],
    style: str,
    title: Optional[str] = None,
) -> tuple[str, Optional[int]]:
    """
    Summarize multiple chunks individually, then combine into a final summary.
    Shows a Rich progress bar during processing.

    Returns:
        (final_summary_text, total_tokens_used)
    """
    from summarizer.ui import chunked_progress

    chunk_summaries = []
    total_tokens = 0

    with chunked_progress(total=len(chunks) + 1, description="Summarizing chunks") as progress:
        for i, chunk in enumerate(chunks, 1):
            logger.debug("Summarizing chunk %d/%d", i, len(chunks))
            partial = client.summarize(
                text=chunk,
                style="concise",  # Use concise for intermediate summaries
                title=title,
            )
            chunk_summaries.append(partial)
            tokens = getattr(client, "last_tokens_used", None)
            if tokens:
                total_tokens += tokens
            progress.advance()

        # Final pass: combine chunk summaries
        combined = "\n\n".join(chunk_summaries)
        logger.debug("Combining %d chunk summaries", len(chunk_summaries))
        final_summary = client.summarize(
            text=combined,
            style=style,
            title=title,
            is_combination=True,
        )
        tokens = getattr(client, "last_tokens_used", None)
        if tokens:
            total_tokens += tokens
        progress.advance()

    return final_summary, total_tokens if total_tokens > 0 else None