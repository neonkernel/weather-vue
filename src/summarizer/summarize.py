"""
Core summarisation logic: fetch → chunk → LLM → cache.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from .cache import SummaryCache
from .exceptions import SummarizerError
from .models import Summary
from . import ui

logger = logging.getLogger(__name__)


def summarize(
    url: str,
    raw_text: Optional[str] = None,
    style: str = "concise",
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    cache: Optional[SummaryCache] = None,
) -> Tuple[Summary, bool]:
    """
    Summarise an article located at *url*.

    Args:
        url:       Article URL (used for fetching and as cache-key component).
        raw_text:  Pre-fetched plain text.  When supplied, fetching is skipped.
        style:     Summarisation style name.
        provider:  LLM provider identifier.
        model:     LLM model identifier.
        cache:     :class:`SummaryCache` instance; pass ``None`` to skip caching.

    Returns:
        A tuple ``(Summary, from_cache)`` where *from_cache* is ``True`` when
        the result was served from the cache.
    """
    # ------------------------------------------------------------------ cache check
    cache_key: Optional[str] = None
    if cache is not None:
        cache_key = cache.make_key(url=url, style=style, provider=provider, model=model)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit for %s", url)
            return cached, True

    # ------------------------------------------------------------------ fetch
    if raw_text is None:
        with ui.spinner(f"Fetching {url}…"):
            raw_text = _fetch(url)

    # ------------------------------------------------------------------ chunk & summarise
    chunks = _split_into_chunks(raw_text)
    logger.debug("Article split into %d chunk(s)", len(chunks))

    chunk_summaries: list[str] = []

    with ui.chunk_progress(total=len(chunks), description="Summarising chunks") as advance:
        llm = _get_llm_client(provider, model)
        for chunk in chunks:
            prompt = _build_prompt(chunk, style)
            try:
                result = llm.complete(prompt)
            except Exception as exc:
                raise SummarizerError(f"LLM completion failed: {exc}") from exc
            chunk_summaries.append(result)
            advance()

    # ------------------------------------------------------------------ merge
    if len(chunk_summaries) == 1:
        final_text = chunk_summaries[0]
    else:
        with ui.spinner("Merging chunk summaries…"):
            final_text = _merge_summaries(chunk_summaries, style, provider, model)

    # ------------------------------------------------------------------ build Summary
    title = _extract_title(raw_text)
    summary = Summary(
        url=url if url != "<stdin>" else None,
        title=title,
        text=final_text,
        style=style,
        provider=provider,
        model=model,
    )

    # ------------------------------------------------------------------ cache store
    if cache is not None and cache_key is not None:
        cache.set(cache_key, summary)
        logger.info("Stored summary in cache (key=%s…)", cache_key[:12])

    return summary, False


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch(url: str) -> str:
    """Fetch and extract plain text from *url*."""
    try:
        from .ingestion import fetch_article
        return fetch_article(url)
    except ImportError:
        # Minimal fallback using urllib
        import urllib.request
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            html = resp.read().decode("utf-8", errors="replace")
        return _strip_html(html)


def _strip_html(html: str) -> str:
    """Very basic HTML-to-text fallback."""
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_CHUNK_SIZE = 3_000  # characters


def _split_into_chunks(text: str, chunk_size: int = _CHUNK_SIZE) -> list[str]:
    """Split *text* into roughly equal chunks of *chunk_size* characters."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to break on a sentence boundary
        if end < len(text):
            boundary = text.rfind(".", start, end)
            if boundary > start:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        start = end

    return [c for c in chunks if c]


def _build_prompt(text: str, style: str) -> str:
    from .styles import STYLES

    style_instruction = STYLES.get(style, STYLES["concise"])
    return (
        f"Summarise the following article text using the '{style}' style.\n"
        f"Style instruction: {style_instruction}\n\n"
        f"Article text:\n{text}\n\n"
        f"Summary:"
    )


def _merge_summaries(summaries: list[str], style: str, provider: str, model: str) -> str:
    """Ask the LLM to merge multiple chunk summaries into one coherent summary."""
    combined = "\n\n---\n\n".join(summaries)
    prompt = (
        f"The following are partial summaries of a long article. "
        f"Merge them into a single coherent summary using the '{style}' style.\n\n"
        f"{combined}\n\nMerged summary:"
    )
    llm = _get_llm_client(provider, model)
    try:
        return llm.complete(prompt)
    except Exception as exc:
        raise SummarizerError(f"LLM merge failed: {exc}") from exc


def _extract_title(text: str) -> Optional[str]:
    """Best-effort title extraction: first non-empty line."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return None


def _get_llm_client(provider: str, model: str):  # type: ignore[return]
    """Return the appropriate LLM client for *provider*."""
    try:
        from .llm.client import LLMClient
        return LLMClient(provider=provider, model=model)
    except ImportError as exc:  # pragma: no cover
        raise SummarizerError(f"LLM client not available: {exc}") from exc