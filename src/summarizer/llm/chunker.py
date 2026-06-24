"""Token-aware text splitter and map-reduce summarization pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import tiktoken

from src.summarizer.llm.token_utils import count_tokens, get_context_window

logger = logging.getLogger(__name__)

# Fraction of the context window to use for each chunk's content.
# The remainder is reserved for prompts and completion.
DEFAULT_CHUNK_CONTENT_RATIO = 0.6

# Number of tokens to overlap between consecutive chunks so that context
# is not lost at chunk boundaries.
DEFAULT_OVERLAP_TOKENS = 100


@dataclass
class TextChunk:
    """A slice of the original text."""

    text: str
    index: int  # 1-based
    total: int
    token_count: int


def split_into_chunks(
    text: str,
    model: str = "gpt-4o-mini",
    max_chunk_tokens: int | None = None,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> List[TextChunk]:
    """Split *text* into overlapping token-bounded chunks.

    Parameters
    ----------
    text:
        The full article text to split.
    model:
        The model name used to select the tokenizer.
    max_chunk_tokens:
        Maximum number of tokens per chunk. Defaults to
        ``DEFAULT_CHUNK_CONTENT_RATIO * context_window``.
    overlap_tokens:
        Number of tokens to repeat at the start of each new chunk to
        preserve context across chunk boundaries.

    Returns
    -------
    List[TextChunk]
        Ordered list of chunks (1-based index).
    """
    try:
        encoder = tiktoken.encoding_for_model(model)
    except KeyError:
        encoder = tiktoken.get_encoding("cl100k_base")

    if max_chunk_tokens is None:
        context_window = get_context_window(model)
        max_chunk_tokens = int(context_window * DEFAULT_CHUNK_CONTENT_RATIO)

    all_token_ids: list[int] = encoder.encode(text)
    total_tokens = len(all_token_ids)

    if total_tokens == 0:
        return []

    logger.debug(
        "Splitting text of %d tokens into chunks of max %d tokens (overlap=%d).",
        total_tokens,
        max_chunk_tokens,
        overlap_tokens,
    )

    chunks: list[TextChunk] = []
    start = 0
    step = max(max_chunk_tokens - overlap_tokens, 1)

    while start < total_tokens:
        end = min(start + max_chunk_tokens, total_tokens)
        chunk_ids = all_token_ids[start:end]
        chunk_text = encoder.decode(chunk_ids)
        chunks.append(chunk_text)
        if end == total_tokens:
            break
        start += step

    logger.info("Split text into %d chunks.", len(chunks))

    total = len(chunks)
    return [
        TextChunk(
            text=chunk_text,
            index=i + 1,
            total=total,
            token_count=count_tokens(chunk_text, model),
        )
        for i, chunk_text in enumerate(chunks)
    ]