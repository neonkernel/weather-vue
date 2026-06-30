"""Core summarization logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.summarizer.exceptions import SummarizerError
from src.summarizer.logger import get_logger
from src.summarizer.styles import build_prompt

if TYPE_CHECKING:
    from src.summarizer.config import Config
    from src.summarizer.llm.base import BaseLLMProvider

logger = get_logger(__name__)

_DEFAULT_CHUNK_SIZE = 3000
_DEFAULT_CHUNK_OVERLAP = 200


class Summarizer:
    """Orchestrates chunking, prompting, and LLM calls to produce a summary."""

    def __init__(self, provider: "BaseLLMProvider", config: "Config") -> None:
        self._provider = provider
        self._config = config

    def summarize(self, text: str) -> str:
        """Summarize *text* and return the summary string."""
        text = text.strip()
        if not text:
            raise SummarizerError("Cannot summarize empty text.")

        chunk_size = self._config.chunk_size or _DEFAULT_CHUNK_SIZE
        chunks = self._chunk_text(text, chunk_size)

        logger.debug("Summarizer: %d chunk(s) for provider=%s", len(chunks), self._config.provider)

        if len(chunks) == 1:
            return self._summarize_chunk(chunks[0])

        # Map-reduce: summarize each chunk then combine
        partial_summaries = [self._summarize_chunk(c) for c in chunks]
        combined = "\n\n".join(partial_summaries)
        logger.debug("Summarizer: combining %d partial summaries.", len(partial_summaries))
        return self._summarize_chunk(combined)

    def _chunk_text(self, text: str, chunk_size: int) -> list[str]:
        """Split *text* into chunks based on provider-aware token counts."""
        overlap = self._config.chunk_overlap or _DEFAULT_CHUNK_OVERLAP

        # Use the provider's token counter
        total_tokens = self._provider.count_tokens(text)
        if total_tokens <= chunk_size:
            return [text]

        # Split by paragraphs, accumulate into chunks
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._provider.count_tokens(para)
            if current_tokens + para_tokens > chunk_size and current_parts:
                chunks.append("\n\n".join(current_parts))
                # Keep some overlap
                overlap_parts: list[str] = []
                overlap_tokens = 0
                for part in reversed(current_parts):
                    part_t = self._provider.count_tokens(part)
                    if overlap_tokens + part_t > overlap:
                        break
                    overlap_parts.insert(0, part)
                    overlap_tokens += part_t
                current_parts = overlap_parts
                current_tokens = overlap_tokens

            current_parts.append(para)
            current_tokens += para_tokens

        if current_parts:
            chunks.append("\n\n".join(current_parts))

        return chunks if chunks else [text]

    def _summarize_chunk(self, text: str) -> str:
        """Send a single chunk to the LLM and return the summary."""
        messages = build_prompt(
            text=text,
            style=self._config.style,
            max_length=self._config.max_length,
        )
        return self._provider.complete(messages)