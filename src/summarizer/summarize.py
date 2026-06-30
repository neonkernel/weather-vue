"""Core summarization logic — provider-agnostic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .exceptions import SummarizerError

if TYPE_CHECKING:
    from .config import SummarizerConfig
    from .llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_STYLE_INSTRUCTIONS: dict[str, str] = {
    "concise": "Write a concise summary in 2-4 sentences.",
    "detailed": "Write a detailed summary covering all key points.",
    "bullet": "Write the summary as a bullet-point list of key takeaways.",
    "academic": (
        "Write an academic-style abstract summarising the main argument, "
        "methodology, findings, and conclusions."
    ),
}


def _build_system_prompt(config: "SummarizerConfig") -> str:
    style_instruction = _STYLE_INSTRUCTIONS.get(
        config.style, _STYLE_INSTRUCTIONS["concise"]
    )
    lang_note = (
        f" Respond in {config.language}." if config.language != "en" else ""
    )
    return (
        f"You are an expert summarizer. {style_instruction}{lang_note} "
        "Focus on accuracy and clarity. Do not add information not present "
        "in the source text."
    )


def _chunk_text(
    text: str, provider: "BaseLLMProvider", chunk_size: int, overlap: int
) -> list[str]:
    """Split text into chunks based on provider-aware token estimates."""
    words = text.split()
    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = start
        current_tokens = 0
        while end < len(words) and current_tokens < chunk_size:
            word_tokens = provider.count_tokens(words[end])
            current_tokens += word_tokens
            end += 1

        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        # Step forward, minus the overlap window (in words, approximated)
        overlap_words = max(1, overlap // 4)  # rough word-level overlap
        start = max(start + 1, end - overlap_words)

    return chunks


def summarize(
    text: str,
    *,
    provider: "BaseLLMProvider",
    config: "SummarizerConfig",
) -> str:
    """
    Summarize ``text`` using the given provider and config.

    For long texts, the document is split into chunks and a final
    consolidation pass is run over the intermediate summaries.

    Args:
        text: Raw input text to summarise.
        provider: An instantiated :class:`~summarizer.llm.base.BaseLLMProvider`.
        config: Runtime configuration.

    Returns:
        The final summary string.

    Raises:
        SummarizerError: If the text is empty or summarization fails.
    """
    text = text.strip()
    if not text:
        raise SummarizerError("Cannot summarize empty text.")

    system_prompt = _build_system_prompt(config)
    total_tokens = provider.count_tokens(text)

    logger.debug(
        "summarize | provider=%s style=%s total_tokens≈%d chunk_size=%d",
        provider.provider_name,
        config.style,
        total_tokens,
        config.chunk_size,
    )

    if total_tokens <= config.chunk_size:
        # Single-pass summarization
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please summarize the following text:\n\n{text}"},
        ]
        return provider.complete(messages)

    # Multi-chunk summarization
    logger.info(
        "Text is ~%d tokens — splitting into chunks of %d.",
        total_tokens,
        config.chunk_size,
    )
    chunks = _chunk_text(text, provider, config.chunk_size, config.chunk_overlap)
    logger.info("Split into %d chunk(s).", len(chunks))

    intermediate_summaries: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        logger.debug("Summarizing chunk %d/%d …", i, len(chunks))
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"This is part {i} of {len(chunks)} of a longer document. "
                    f"Please summarize this section:\n\n{chunk}"
                ),
            },
        ]
        summary = provider.complete(messages)
        intermediate_summaries.append(summary)

    # Consolidation pass
    combined = "\n\n---\n\n".join(
        f"Section {i}:\n{s}" for i, s in enumerate(intermediate_summaries, start=1)
    )
    consolidation_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Below are summaries of individual sections of a longer document. "
                "Please consolidate them into a single coherent summary:\n\n"
                f"{combined}"
            ),
        },
    ]
    return provider.complete(consolidation_messages)