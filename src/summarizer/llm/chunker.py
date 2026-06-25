"""Token-aware text splitter and map-reduce summarization pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import tiktoken

from .token_utils import _get_encoding, count_tokens, max_content_tokens

if TYPE_CHECKING:
    from .client import SummarizerClient
    from .prompts import SummaryStyle

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 3_000    # tokens per chunk
DEFAULT_CHUNK_OVERLAP = 200   # overlap tokens between consecutive chunks


@dataclass
class TextChunker:
    """Splits text into overlapping token-aware chunks."""

    model: str = "gpt-4o-mini"
    chunk_size: int = DEFAULT_CHUNK_SIZE
    overlap: int = DEFAULT_CHUNK_OVERLAP

    def split(self, text: str) -> list[str]:
        """Split *text* into overlapping chunks of at most *chunk_size* tokens."""
        encoding = _get_encoding(self.model)
        tokens = encoding.encode(text)

        if len(tokens) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0

        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            if end == len(tokens):
                break

            # Advance by chunk_size minus overlap so consecutive chunks share context
            start += self.chunk_size - self.overlap

        logger.debug(
            "Split text (%d tokens) into %d chunks (size=%d, overlap=%d).",
            len(tokens),
            len(chunks),
            self.chunk_size,
            self.overlap,
        )
        return chunks


def map_reduce_summarize(
    text: str,
    client: "SummarizerClient",
    style: "SummaryStyle" = "concise",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> str:
    """Summarize *text* using a map-reduce strategy.

    1. Map: split text into chunks, summarize each independently.
    2. Reduce: combine chunk summaries into a final summary.

    Returns the final summary string.
    """
    chunker = TextChunker(model=client.model, chunk_size=chunk_size, overlap=overlap)
    chunks = chunker.split(text)

    logger.info("Map-reduce: %d chunks to process.", len(chunks))

    # --- Map phase ---
    partial_summaries: list[str] = []
    for idx, chunk in enumerate(chunks):
        logger.info("Summarizing chunk %d/%d …", idx + 1, len(chunks))
        messages = client.prompt_builder.build_chunk_messages(chunk, idx, len(chunks))
        summary_text, usage = client._call_api(messages)
        partial_summaries.append(summary_text)
        logger.info(
            "Chunk %d/%d done. Tokens used: prompt=%d, completion=%d.",
            idx + 1,
            len(chunks),
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    # --- Reduce phase ---
    logger.info("Reduce phase: combining %d partial summaries.", len(partial_summaries))
    reduce_messages = client.prompt_builder.build_reduce_messages(partial_summaries)
    final_summary, usage = client._call_api(reduce_messages)
    logger.info(
        "Reduce done. Tokens used: prompt=%d, completion=%d.",
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )
    return final_summary