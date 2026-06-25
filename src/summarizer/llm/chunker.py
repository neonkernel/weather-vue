"""Token-aware text splitter and map-reduce summarization pipeline."""

import logging
from dataclasses import dataclass
from typing import Optional

import tiktoken

from .token_utils import count_tokens, get_context_window

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    text: str
    index: int
    token_count: int
    start_char: int
    end_char: int


class TextChunker:
    """
    Splits text into overlapping chunks based on token count.

    Uses tiktoken for accurate token counting to ensure chunks
    fit within the model's context window.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        chunk_size: Optional[int] = None,
        overlap_tokens: int = 100,
        reserved_tokens: int = 1500,
    ):
        """
        Initialize the TextChunker.

        Args:
            model: The model name (used for token counting and context window).
            chunk_size: Maximum tokens per chunk. If None, calculated from
                        the model's context window minus reserved tokens.
            overlap_tokens: Number of tokens to overlap between chunks.
            reserved_tokens: Tokens reserved for system prompt, instructions,
                             and completion output.
        """
        self.model = model
        self.overlap_tokens = overlap_tokens
        self.reserved_tokens = reserved_tokens

        context_window = get_context_window(model)
        if chunk_size is None:
            self.chunk_size = context_window - reserved_tokens
        else:
            self.chunk_size = min(chunk_size, context_window - reserved_tokens)

        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

        logger.debug(
            f"TextChunker initialized: model={model}, chunk_size={self.chunk_size}, "
            f"overlap={overlap_tokens}"
        )

    def split(self, text: str) -> list[Chunk]:
        """
        Split text into overlapping token-based chunks.

        Args:
            text: The text to split.

        Returns:
            A list of Chunk objects.
        """
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)

        if total_tokens <= self.chunk_size:
            logger.debug(f"Text fits in single chunk ({total_tokens} tokens)")
            return [
                Chunk(
                    text=text,
                    index=0,
                    token_count=total_tokens,
                    start_char=0,
                    end_char=len(text),
                )
            ]

        chunks = []
        start_token = 0
        chunk_index = 0

        while start_token < total_tokens:
            end_token = min(start_token + self.chunk_size, total_tokens)

            # Decode the token slice back to text
            chunk_tokens = tokens[start_token:end_token]
            chunk_text = self.encoding.decode(chunk_tokens)

            # Find character positions (approximate)
            start_char = len(self.encoding.decode(tokens[:start_token]))
            end_char = start_char + len(chunk_text)

            chunk = Chunk(
                text=chunk_text,
                index=chunk_index,
                token_count=len(chunk_tokens),
                start_char=start_char,
                end_char=end_char,
            )
            chunks.append(chunk)

            logger.debug(
                f"Created chunk {chunk_index}: tokens {start_token}-{end_token} "
                f"({len(chunk_tokens)} tokens)"
            )

            # Move forward by chunk_size minus overlap
            step = self.chunk_size - self.overlap_tokens
            start_token += step
            chunk_index += 1

            # Safety: if step is non-positive, break to avoid infinite loop
            if step <= 0:
                logger.warning("Chunk step size is non-positive; breaking to avoid infinite loop")
                break

        logger.info(f"Split text into {len(chunks)} chunks ({total_tokens} total tokens)")
        return chunks

    def needs_chunking(self, text: str) -> bool:
        """
        Check if text needs to be chunked.

        Args:
            text: The text to check.

        Returns:
            True if the text exceeds the chunk size.
        """
        token_count = count_tokens(text, self.model)
        return token_count > self.chunk_size


class MapReduceSummarizer:
    """
    Implements map-reduce summarization for long documents.

    1. MAP: Summarize each chunk independently.
    2. REDUCE: Merge chunk summaries into a final summary.
    """

    def __init__(self, client, prompt_builder, chunker: TextChunker):
        """
        Initialize the MapReduceSummarizer.

        Args:
            client: SummarizerClient instance for making API calls.
            prompt_builder: PromptBuilder instance for constructing prompts.
            chunker: TextChunker instance for splitting text.
        """
        self.client = client
        self.prompt_builder = prompt_builder
        self.chunker = chunker

    def summarize(self, text: str) -> tuple[str, dict]:
        """
        Perform map-reduce summarization on a long text.

        Args:
            text: The full text to summarize.

        Returns:
            A tuple of (final_summary, usage_stats) where usage_stats
            contains aggregated token usage.
        """
        chunks = self.chunker.split(text)
        total_chunks = len(chunks)

        logger.info(f"Starting map-reduce summarization with {total_chunks} chunks")

        # MAP phase: summarize each chunk
        chunk_summaries = []
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for chunk in chunks:
            messages = self.prompt_builder.build_chunk_messages(
                chunk.text, chunk.index, total_chunks
            )
            summary, usage = self.client.complete(messages)
            chunk_summaries.append(summary)

            # Aggregate token usage
            for key in total_usage:
                total_usage[key] += usage.get(key, 0)

            logger.info(
                f"Summarized chunk {chunk.index + 1}/{total_chunks} "
                f"({usage.get('total_tokens', 0)} tokens)"
            )

        # REDUCE phase: merge chunk summaries
        logger.info("Merging chunk summaries into final summary")
        merge_messages = self.prompt_builder.build_merge_messages(chunk_summaries)
        final_summary, merge_usage = self.client.complete(merge_messages)

        # Add merge usage to totals
        for key in total_usage:
            total_usage[key] += merge_usage.get(key, 0)

        logger.info(
            f"Map-reduce complete. Total tokens used: {total_usage['total_tokens']}"
        )

        return final_summary, total_usage