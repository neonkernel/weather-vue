"""Token-aware text splitter and map-reduce summarization pipeline."""

import logging
from typing import Optional, TYPE_CHECKING

from .token_utils import count_tokens, get_available_tokens, get_encoding

if TYPE_CHECKING:
    from .client import SummarizerClient
    from .prompts import PromptBuilder

logger = logging.getLogger(__name__)


class TextChunker:
    """Splits text into token-aware chunks with configurable overlap.

    Args:
        model: The model name to use for tokenization.
        max_chunk_tokens: Maximum number of tokens per chunk.
        overlap_tokens: Number of tokens to overlap between chunks.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_chunk_tokens: int = 4_000,
        overlap_tokens: int = 200,
    ):
        self.model = model
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
        self._encoding = get_encoding(model)

    def split(self, text: str) -> list[str]:
        """Split text into overlapping chunks by token count.

        Uses a sentence-aware splitting strategy where possible:
        1. Tokenize the full text
        2. Decode chunks by token boundaries
        3. Overlap tokens carry context between chunks

        Args:
            text: The text to split.

        Returns:
            List of text chunks.
        """
        tokens = self._encoding.encode(text)
        total_tokens = len(tokens)

        if total_tokens <= self.max_chunk_tokens:
            logger.debug(
                "Text fits in single chunk (%d tokens <= %d max)",
                total_tokens,
                self.max_chunk_tokens,
            )
            return [text]

        chunks = []
        start = 0
        step = self.max_chunk_tokens - self.overlap_tokens

        if step <= 0:
            raise ValueError(
                f"overlap_tokens ({self.overlap_tokens}) must be less than "
                f"max_chunk_tokens ({self.max_chunk_tokens})"
            )

        while start < total_tokens:
            end = min(start + self.max_chunk_tokens, total_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = self._encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            logger.debug(
                "Created chunk %d: tokens %d-%d (%d tokens)",
                len(chunks),
                start,
                end,
                len(chunk_tokens),
            )

            if end >= total_tokens:
                break

            start += step

        logger.info(
            "Split text into %d chunks (total tokens: %d, max per chunk: %d, overlap: %d)",
            len(chunks),
            total_tokens,
            self.max_chunk_tokens,
            self.overlap_tokens,
        )
        return chunks


class MapReduceSummarizer:
    """Implements map-reduce summarization for long articles.

    For articles that exceed the model's context window:
    1. MAP: Split the article into chunks and summarize each independently
    2. REDUCE: Merge the chunk summaries into a final cohesive summary

    Args:
        client: The SummarizerClient instance.
        prompt_builder: The PromptBuilder instance.
        chunker: The TextChunker instance.
    """

    def __init__(
        self,
        client: "SummarizerClient",
        prompt_builder: "PromptBuilder",
        chunker: Optional[TextChunker] = None,
    ):
        self.client = client
        self.prompt_builder = prompt_builder
        self.chunker = chunker or TextChunker(model=client.model)

    def summarize(self, text: str, title: Optional[str] = None) -> str:
        """Run map-reduce summarization.

        Args:
            text: The full article text.
            title: Optional article title.

        Returns:
            Final merged summary string.
        """
        chunks = self.chunker.split(text)
        total_chunks = len(chunks)

        logger.info(
            "Starting map-reduce summarization: %d chunks for article '%s'",
            total_chunks,
            title or "(untitled)",
        )

        # MAP phase: summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info("Summarizing chunk %d/%d", i + 1, total_chunks)
            messages = self.prompt_builder.build_chunk_messages(
                chunk_text=chunk,
                chunk_index=i,
                total_chunks=total_chunks,
            )
            summary = self.client.complete(messages)
            chunk_summaries.append(summary)
            logger.debug("Chunk %d summary: %s...", i + 1, summary[:100])

        # REDUCE phase: merge chunk summaries
        logger.info("Merging %d chunk summaries", len(chunk_summaries))
        merge_messages = self.prompt_builder.build_merge_messages(
            chunk_summaries=chunk_summaries,
            title=title,
        )
        final_summary = self.client.complete(merge_messages)

        logger.info("Map-reduce summarization complete")
        return final_summary