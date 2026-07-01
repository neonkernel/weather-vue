"""Core summarization logic."""

from __future__ import annotations

import logging
import time
from typing import Optional

from .config import settings
from .exceptions import SummarizerError
from .ingestion import fetch_article
from .llm.client import LLMClient
from .models import Summary
from .styles import SummaryStyle
from .ui import chunk_progress, spinner

logger = logging.getLogger(__name__)

# Rough character-to-token ratio (conservative)
CHARS_PER_TOKEN = 4
# Maximum tokens to send to the model per chunk
CHUNK_TOKEN_LIMIT = 3000
CHUNK_CHAR_LIMIT = CHUNK_TOKEN_LIMIT * CHARS_PER_TOKEN


def _chunk_text(text: str, max_chars: int = CHUNK_CHAR_LIMIT) -> list[str]:
    """Split text into chunks of at most max_chars characters."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    while text:
        chunk = text[:max_chars]
        # Try to break on a sentence boundary
        boundary = max(chunk.rfind(". "), chunk.rfind(".\n"), chunk.rfind("! "), chunk.rfind("? "))
        if boundary > max_chars // 2:
            chunk = text[: boundary + 1]
        chunks.append(chunk.strip())
        text = text[len(chunk) :].strip()
    return chunks


def _build_prompt(text: str, style: str, title: Optional[str]) -> str:
    style_instructions = {
        SummaryStyle.CONCISE.value: "Provide a concise 2-3 sentence summary.",
        SummaryStyle.DETAILED.value: "Provide a detailed summary covering all major points.",
        SummaryStyle.BULLET.value: "Summarize using clear bullet points (• prefix).",
        SummaryStyle.ELI5.value: "Explain this article as if the reader is 5 years old.",
        SummaryStyle.TECHNICAL.value: "Provide a technical summary focusing on methods and findings.",
    }
    instruction = style_instructions.get(style, "Summarize the following article.")
    title_part = f'Title: "{title}"\n\n' if title else ""
    return (
        f"{title_part}"
        f"Article text:\n\n{text}\n\n"
        f"Instructions: {instruction}"
    )


def _merge_chunk_summaries(summaries: list[str], style: str, client: LLMClient) -> str:
    """Merge multiple chunk summaries into a final coherent summary."""
    if len(summaries) == 1:
        return summaries[0]

    combined = "\n\n---\n\n".join(summaries)
    style_instructions = {
        SummaryStyle.CONCISE.value: "Merge these partial summaries into a concise 2-3 sentence final summary.",
        SummaryStyle.DETAILED.value: "Merge these partial summaries into a detailed, coherent summary.",
        SummaryStyle.BULLET.value: "Merge and deduplicate these bullet-point summaries into a final list.",
        SummaryStyle.ELI5.value: "Merge these partial summaries into a simple explanation for a 5-year-old.",
        SummaryStyle.TECHNICAL.value: "Merge these partial summaries into a technical summary.",
    }
    instruction = style_instructions.get(style, "Merge these partial summaries into a final summary.")
    prompt = f"Partial summaries:\n\n{combined}\n\n{instruction}"
    return client.complete(prompt, estimated_tokens=len(combined) // CHARS_PER_TOKEN)


def summarize_url(
    url: str,
    style: str = SummaryStyle.CONCISE.value,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    quiet: bool = False,
) -> Summary:
    """
    Fetch an article and summarize it.

    Parameters
    ----------
    url:        Article URL to fetch and summarize.
    style:      One of the SummaryStyle values.
    provider:   LLM provider name (falls back to settings).
    model:      Model identifier (falls back to settings).
    quiet:      Suppress progress UI.

    Returns
    -------
    Summary dataclass populated with the result.
    """
    start = time.monotonic()

    effective_provider = provider or settings.default_provider
    effective_model = model or settings.default_model

    # ------------------------------------------------------------------ fetch
    with spinner("Fetching article…", quiet=quiet):
        try:
            article = fetch_article(url)
        except Exception as exc:
            raise SummarizerError(f"Failed to fetch article: {exc}") from exc

    logger.debug(
        "Fetched '%s' (%d chars)", article.title or url, len(article.text)
    )

    # ------------------------------------------------------------------ chunk
    chunks = _chunk_text(article.text)
    chunk_count = len(chunks)
    logger.debug("Split article into %d chunk(s).", chunk_count)

    # ------------------------------------------------------------------ LLM
    client = LLMClient(provider=effective_provider, model=effective_model)
    chunk_summaries: list[str] = []

    with chunk_progress(
        total=chunk_count, description="Summarizing", quiet=quiet
    ) as progress:
        for i, chunk in enumerate(chunks):
            prompt = _build_prompt(chunk, style, article.title if i == 0 else None)
            estimated_tokens = len(chunk) // CHARS_PER_TOKEN + 200
            try:
                partial = client.complete(prompt, estimated_tokens=estimated_tokens)
            except Exception as exc:
                raise SummarizerError(f"LLM call failed on chunk {i + 1}: {exc}") from exc
            chunk_summaries.append(partial)
            progress.advance()

    # ------------------------------------------------------------------ merge
    if chunk_count > 1:
        with spinner("Merging chunk summaries…", quiet=quiet):
            final_summary = _merge_chunk_summaries(chunk_summaries, style, client)
    else:
        final_summary = chunk_summaries[0]

    elapsed = time.monotonic() - start
    word_count = len(final_summary.split())

    return Summary(
        url=url,
        title=article.title or "",
        summary=final_summary,
        style=style,
        provider=effective_provider,
        model=effective_model,
        word_count=word_count,
        chunk_count=chunk_count,
        elapsed_seconds=round(elapsed, 2),
    )