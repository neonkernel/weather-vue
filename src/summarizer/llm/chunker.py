"""Token-aware text splitter and map-reduce summarization pipeline."""

import logging
from typing import Generator, Optional

import tiktoken

from .token_utils import count_tokens, get_encoding, max_chunk_tokens

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_OVERLAP = 100  # tokens
DEFAULT_CHUNK_SIZE_RATIO = 0.85  # Use 85% of available context for chunks


class TextChunker:
    """Splits text into overlapping token-aware chunks.

    Args:
        model: The model name to use for token counting.
        chunk_size: Maximum tokens per chunk. If None, uses model context window.
        overlap: Number of tokens to overlap between consecutive chunks.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        chunk_size: Optional[int] = None,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        self.model = model
        self.overlap = overlap
        self.encoding = get_encoding(model)

        if chunk_size is None:
            available = max_chunk_tokens(model)
            self.chunk_size = int(available * DEFAULT_CHUNK_SIZE_RATIO)
        else:
            self.chunk_size = chunk_size

        logger.debug(
            "TextChunker initialized: model=%s, chunk_size=%d, overlap=%d",
            model,
            self.chunk_size,
            overlap,
        )

    def split(self, text: str) -> list[str]:
        """Split text into overlapping chunks by token count.

        Args:
            text: The text to split.

        Returns:
            A list of text chunks.
        """
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)

        if total_tokens <= self.chunk_size:
            logger.debug("Text fits in a single chunk (%d tokens)", total_tokens)
            return [text]

        chunks = []
        start = 0
        chunk_index = 0

        while start < total_tokens:
            end = min(start + self.chunk_size, total_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            chunk_index += 1
            logger.debug(
                "Chunk %d: tokens %d-%d (%d tokens)",
                chunk_index,
                start,
                end,
                len(chunk_tokens),
            )

            if end >= total_tokens:
                break

            # Advance by chunk_size minus overlap
            start = end - self.overlap

        logger.info(
            "Split text (%d tokens) into %d chunks (chunk_size=%d, overlap=%d)",
            total_tokens,
            len(chunks),
            self.chunk_size,
            self.overlap,
        )
        return chunks

    def needs_chunking(self, text: str) -> bool:
        """Check if text needs to be chunked.

        Args:
            text: The text to check.

        Returns:
            True if the text exceeds the chunk size.
        """
        return count_tokens(text, self.model) > self.chunk_size


def run_map_reduce(
    text: str,
    summarize_fn,
    model: str = "gpt-4o-mini",
    chunk_size: Optional[int] = None,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    title: Optional[str] = None,
) -> str:
    """Run a map-reduce summarization pipeline on long text.

    Splits the text into chunks, summarizes each chunk independently (map),
    then summarizes the collected summaries (reduce).

    Args:
        text: The full text to summarize.
        summarize_fn: Callable(text, title, is_chunk, chunk_index, total_chunks) -> str
            A function that summarizes a piece of text.
        model: The model name for token counting.
        chunk_size: Maximum tokens per chunk.
        overlap: Token overlap between chunks.
        title: Optional article title for context.

    Returns:
        The final combined summary.
    """
    chunker = TextChunker(model=model, chunk_size=chunk_size, overlap=overlap)
    chunks = chunker.split(text)

    if len(chunks) == 1:
        logger.info("Text fits in a single chunk, skipping map-reduce")
        return summarize_fn(
            text=chunks[0],
            title=title,
            is_chunk=False,
            chunk_index=1,
            total_chunks=1,
        )

    logger.info("Starting map phase: summarizing %d chunks", len(chunks))

    # Map phase: summarize each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks, 1):
        logger.debug("Summarizing chunk %d/%d", i, len(chunks))
        chunk_summary = summarize_fn(
            text=chunk,
            title=title,
            is_chunk=True,
            chunk_index=i,
            total_chunks=len(chunks),
        )
        chunk_summaries.append(chunk_summary)
        logger.debug("Chunk %d summarized (%d chars)", i, len(chunk_summary))

    logger.info("Map phase complete. Starting reduce phase.")

    # Reduce phase: summarize the summaries
    combined_text = "\n\n".join(
        f"Section {i} Summary:\n{s}" for i, s in enumerate(chunk_summaries, 1)
    )

    final_summary = summarize_fn(
        text=combined_text,
        title=title,
        is_chunk=False,
        chunk_index=0,
        total_chunks=len(chunks),
        is_reduce=True,
        chunk_summaries=chunk_summaries,
    )

    logger.info("Reduce phase complete.")
    return final_summary