"""Core summarization logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .exceptions import SummarizerError
from .logger import get_logger

if TYPE_CHECKING:
    from .config import SummarizerConfig
    from .llm.base import BaseLLMProvider

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert summarizer. Your task is to produce a clear, accurate, "
    "and concise summary of the provided text. Preserve the key points and "
    "maintain factual accuracy. Do not add information not present in the source."
)

_STYLE_INSTRUCTIONS: dict[str, str] = {
    "paragraph": "Write the summary as one or more coherent paragraphs.",
    "bullet_points": (
        "Write the summary as a list of concise bullet points. "
        "Start each point with a dash (-)."
    ),
    "tldr": (
        "Write a single TL;DR sentence capturing the most important takeaway."
    ),
}


def _build_messages(
    content: str,
    style: str,
) -> list[dict[str, str]]:
    """Construct the message list to send to the LLM."""
    style_instruction = _STYLE_INSTRUCTIONS.get(
        style,
        f"Write the summary in '{style}' style.",
    )

    user_content = (
        f"{style_instruction}\n\n"
        f"Text to summarize:\n\n{content}"
    )

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _ingest(source: str) -> str:
    """
    Load content from a local file path or a URL.
    Returns plain text.
    """
    if source.startswith("http://") or source.startswith("https://"):
        return _fetch_url(source)
    return _read_file(source)


def _fetch_url(url: str) -> str:
    """Fetch and extract text from a URL."""
    try:
        import requests
    except ImportError as exc:
        raise SummarizerError(
            "requests is required to fetch URLs. pip install requests"
        ) from exc

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html = response.text
    except Exception as exc:
        raise SummarizerError(f"Failed to fetch URL '{url}': {exc}") from exc

    # Try to strip HTML tags if beautifulsoup4 is available
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        pass

    # Naive fallback: strip tags with regex
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _read_file(path: str) -> str:
    """Read a local file and return its text content."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise SummarizerError(f"Failed to read file '{path}': {exc}") from exc


def _chunk_text(
    text: str,
    provider: "BaseLLMProvider",
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """
    Split text into chunks whose token count does not exceed chunk_size.
    Uses the provider's count_tokens method for provider-aware splitting.
    """
    # Simple sentence-boundary chunking
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = provider.count_tokens(sentence)

        if current_tokens + sentence_tokens > chunk_size and current_parts:
            chunks.append(" ".join(current_parts))
            # Keep overlap: retain last N tokens worth of sentences
            overlap_parts: list[str] = []
            overlap_tokens = 0
            for part in reversed(current_parts):
                part_tokens = provider.count_tokens(part)
                if overlap_tokens + part_tokens <= overlap:
                    overlap_parts.insert(0, part)
                    overlap_tokens += part_tokens
                else:
                    break
            current_parts = overlap_parts
            current_tokens = overlap_tokens

        current_parts.append(sentence)
        current_tokens += sentence_tokens

    if current_parts:
        chunks.append(" ".join(current_parts))

    return chunks


def summarize(
    source: str,
    provider: "BaseLLMProvider",
    style: str = "paragraph",
    config: Optional["SummarizerConfig"] = None,
) -> str:
    """
    Summarize the content at *source* using *provider*.

    Args:
        source: File path or URL to the content.
        provider: An instantiated BaseLLMProvider.
        style: Summary style key (paragraph, bullet_points, tldr, etc.)
        config: Optional SummarizerConfig for token/chunk settings.

    Returns:
        The summary text.
    """
    from .config import SummarizerConfig

    cfg = config or SummarizerConfig()

    logger.info("Ingesting source: %s", source)
    text = _ingest(source)
    logger.info("Ingested %d characters", len(text))

    total_tokens = provider.count_tokens(text)
    logger.debug("Estimated token count: %d", total_tokens)

    llm_kwargs = {
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
    }

    if total_tokens <= cfg.chunk_size:
        # Single-pass summarization
        messages = _build_messages(text, style)
        logger.info("Single-pass summarization via %s", provider.provider_name)
        return provider.complete(messages, **llm_kwargs)

    # Multi-chunk: summarize each chunk, then summarize the summaries
    logger.info(
        "Text too large (%d tokens). Chunking with size=%d, overlap=%d.",
        total_tokens,
        cfg.chunk_size,
        cfg.chunk_overlap,
    )
    chunks = _chunk_text(text, provider, cfg.chunk_size, cfg.chunk_overlap)
    logger.info("Split into %d chunks", len(chunks))

    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        logger.info("Summarizing chunk %d/%d", i, len(chunks))
        messages = _build_messages(chunk, style="paragraph")
        chunk_summary = provider.complete(messages, **llm_kwargs)
        chunk_summaries.append(chunk_summary)

    # Final pass: summarize all chunk summaries together
    combined = "\n\n".join(chunk_summaries)
    logger.info("Final summarization pass over %d chunk summaries", len(chunk_summaries))
    final_messages = _build_messages(combined, style)
    return provider.complete(final_messages, **llm_kwargs)