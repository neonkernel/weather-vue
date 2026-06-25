"""Token-aware text splitter and map-reduce summarization pipeline."""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import tiktoken

from .token_utils import count_tokens, get_context_window

if TYPE_CHECKING:
    from .client import SummarizerClient
    from .prompts import PromptBuilder

logger = logging.getLogger(__name__)

# Default chunk configuration
DEFAULT_CHUNK_TOKENS = 3_000
DEFAULT_OVERLAP_TOKENS = 200


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""

    text: str
    index: int  # 0-based
    token_count: int
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class TextChunker:
    """
    Splits text into overlapping chunks by token count.

    Uses tiktoken for accurate token counting so that chunk sizes
    respect the model's context window.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    ) -> None:
        self.model = model
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens

        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(
                "No encoding for model '%s'; falling back to cl100k_base.", model
            )
            self._encoding = tiktoken.get_encoding("cl100k_base")

    def split(self, text: str) -> list[Chunk]:
        """
        Split *text* into token-bounded chunks with overlap.

        Args:
            text: The full article text.

        Returns:
            Ordered list of Chunk objects.
        """
        if not text.strip():
            return []

        tokens = self._encoding.encode(text)
        total_tokens = len(tokens)

        if total_tokens == 0:
            return []

        chunks: list[Chunk] = []
        start = 0
        chunk_index = 0

        while start < total_tokens:
            end = min(start + self.chunk_tokens, total_tokens)
            chunk_token_ids = tokens[start:end]
            chunk_text = self._encoding.decode(chunk_token_ids)
            chunk_token_count = len(chunk_token_ids)

            chunks.append(
                Chunk(
                    text=chunk_text,
                    index=chunk_index,
                    token_count=chunk_token_count,
                )
            )
            logger.debug(
                "Created chunk %d: tokens %d–%d (%d tokens)",
                chunk_index,
                start,
                end,
                chunk_token_count,
            )
            chunk_index += 1

            # Advance by (chunk_tokens - overlap_tokens), but at least 1 token
            advance = max(1, self.chunk_tokens - self.overlap_tokens)
            start += advance

            if end == total_tokens:
                break  # We've consumed all tokens

        return chunks


class MapReduceSummarizer:
    """
    Implements map-reduce summarization for long articles.

    Step 1 (map): Summarize each chunk independently.
    Step 2 (reduce): Merge all chunk summaries into a final summary.
    """

    def __init__(
        self,
        client: "SummarizerClient",
        prompt_builder: "PromptBuilder",
        chunker: Optional[TextChunker] = None,
    ) -> None:
        self.client = client
        self.prompt_builder = prompt_builder
        self.chunker = chunker or TextChunker(model=client.model)

    def summarize(self, text: str) -> tuple[str, dict]:
        """
        Run the map-reduce pipeline on *text*.

        Args:
            text: The full article text to summarize.

        Returns:
            A tuple of (final_summary_text, usage_stats) where usage_stats
            aggregates token usage across all API calls.
        """
        chunks = self.chunker.split(text)
        if not chunks:
            return "", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        logger.info(
            "Map-reduce: processing %d chunks (chunk_tokens=%d, overlap=%d).",
            len(chunks),
            self.chunker.chunk_tokens,
            self.chunker.overlap_tokens,
        )

        total_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        # --- Map phase ---
        chunk_summaries: list[str] = []
        for chunk in chunks:
            messages = self.prompt_builder.build_chunk(
                text=chunk.text,
                chunk_index=chunk.index + 1,
                total_chunks=len(chunks),
            )
            summary_text, usage = self.client.complete(messages)
            chunk_summaries.append(summary_text)
            _accumulate_usage(total_usage, usage)
            logger.debug(
                "Chunk %d/%d summarized (%d tokens used).",
                chunk.index + 1,
                len(chunks),
                usage.get("total_tokens", 0),
            )

        # If there's only one chunk, the map result *is* the final result
        if len(chunk_summaries) == 1:
            return chunk_summaries[0], total_usage

        # --- Reduce phase ---
        logger.info("Map-reduce: merging %d chunk summaries.", len(chunk_summaries))
        merge_messages = self.prompt_builder.build_merge(chunk_summaries)
        final_summary, merge_usage = self.client.complete(merge_messages)
        _accumulate_usage(total_usage, merge_usage)

        return final_summary, total_usage


def _accumulate_usage(total: dict[str, int], new: dict[str, int]) -> None:
    """Add token counts from *new* into the *total* dict in-place."""
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        total[key] = total.get(key, 0) + new.get(key, 0)