"""Token-aware text splitter and map-reduce summarization pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import tiktoken

from .token_utils import (
    DEFAULT_MODEL,
    RESERVED_TOKENS,
    count_tokens,
    get_context_window,
)

if TYPE_CHECKING:
    from .client import SummarizerClient
    from .prompts import PromptBuilder

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    text: str
    chunk_index: int
    total_chunks: int
    token_count: int = 0

    def __post_init__(self) -> None:
        if self.token_count == 0:
            self.token_count = count_tokens(self.text)


@dataclass
class Chunker:
    """Token-aware text splitter using tiktoken.

    Splits article text into overlapping chunks suitable for map-reduce
    summarization.
    """

    model: str = DEFAULT_MODEL
    # Tokens to reserve for system prompt + response per chunk call
    reserved_tokens: int = RESERVED_TOKENS
    # Number of tokens to overlap between consecutive chunks
    overlap_tokens: int = 100

    @property
    def max_chunk_tokens(self) -> int:
        """Maximum tokens per chunk (context window minus reserved)."""
        return get_context_window(self.model) - self.reserved_tokens

    def _get_encoding(self) -> tiktoken.Encoding:
        try:
            return tiktoken.encoding_for_model(self.model)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")

    def split(self, text: str) -> list[TextChunk]:
        """Split text into token-aware chunks with overlap.

        Args:
            text: The text to split.

        Returns:
            A list of TextChunk objects.
        """
        encoding = self._get_encoding()
        all_tokens = encoding.encode(text)
        total_tokens = len(all_tokens)

        if total_tokens <= self.max_chunk_tokens:
            logger.debug(
                "Text fits in a single chunk (%d tokens).", total_tokens
            )
            chunk = TextChunk(
                text=text,
                chunk_index=0,
                total_chunks=1,
                token_count=total_tokens,
            )
            return [chunk]

        chunks: list[TextChunk] = []
        step = self.max_chunk_tokens - self.overlap_tokens
        if step <= 0:
            step = self.max_chunk_tokens

        start = 0
        chunk_index = 0

        # Pre-calculate number of chunks
        chunk_starts = []
        pos = 0
        while pos < total_tokens:
            chunk_starts.append(pos)
            pos += step

        total_chunks = len(chunk_starts)

        for chunk_start in chunk_starts:
            chunk_end = min(chunk_start + self.max_chunk_tokens, total_tokens)
            chunk_tokens = all_tokens[chunk_start:chunk_end]
            chunk_text = encoding.decode(chunk_tokens)

            chunks.append(
                TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                    token_count=len(chunk_tokens),
                )
            )
            chunk_index += 1

            if chunk_end >= total_tokens:
                break

        logger.info(
            "Split text into %d chunks (total %d tokens, max %d per chunk).",
            len(chunks),
            total_tokens,
            self.max_chunk_tokens,
        )
        return chunks


def map_reduce_summarize(
    text: str,
    title: str,
    client: "SummarizerClient",
    prompt_builder: "PromptBuilder",
    model: str = DEFAULT_MODEL,
    reserved_tokens: int = RESERVED_TOKENS,
    overlap_tokens: int = 100,
) -> tuple[str, int, int]:
    """Perform map-reduce summarization on long text.

    1. Map: Split text into chunks and summarize each independently.
    2. Reduce: Combine chunk summaries into a final summary.

    Args:
        text: The full article text.
        title: The article title.
        client: The SummarizerClient to use for API calls.
        prompt_builder: The PromptBuilder for prompt construction.
        model: The model to use.
        reserved_tokens: Tokens to reserve per API call.
        overlap_tokens: Token overlap between chunks.

    Returns:
        A tuple of (summary_text, total_prompt_tokens, total_completion_tokens).
    """
    chunker = Chunker(
        model=model,
        reserved_tokens=reserved_tokens,
        overlap_tokens=overlap_tokens,
    )
    chunks = chunker.split(text)

    total_prompt_tokens = 0
    total_completion_tokens = 0
    chunk_summaries: list[str] = []

    logger.info("Map phase: summarizing %d chunks.", len(chunks))

    for chunk in chunks:
        messages = prompt_builder.build_chunk_messages(chunk.text)
        summary, prompt_tokens, completion_tokens = client.complete(messages)
        chunk_summaries.append(summary)
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        logger.debug(
            "Chunk %d/%d summarized (%d + %d tokens).",
            chunk.chunk_index + 1,
            chunk.total_chunks,
            prompt_tokens,
            completion_tokens,
        )

    logger.info("Reduce phase: combining %d chunk summaries.", len(chunk_summaries))

    if len(chunk_summaries) == 1:
        return chunk_summaries[0], total_prompt_tokens, total_completion_tokens

    reduce_messages = prompt_builder.build_reduce_messages(chunk_summaries, title)
    final_summary, prompt_tokens, completion_tokens = client.complete(reduce_messages)
    total_prompt_tokens += prompt_tokens
    total_completion_tokens += completion_tokens

    return final_summary, total_prompt_tokens, total_completion_tokens