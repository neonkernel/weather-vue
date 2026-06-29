"""Core summarization logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import LLMError, SummarizerError

if TYPE_CHECKING:
    from .config import Config
    from .llm.base import BaseLLMProvider


_STYLE_INSTRUCTIONS: dict[str, str] = {
    "concise": "Provide a concise summary in 2–4 sentences.",
    "detailed": "Provide a detailed summary covering all key points.",
    "bullet": "Summarize using a bulleted list of key points.",
}

_DEFAULT_SYSTEM_PROMPT = (
    "You are a professional summarizer. Your task is to summarize the provided text "
    "clearly and accurately. Do not add information not present in the source text."
)


def _build_messages(
    text: str,
    style: str = "concise",
    language: str = "en",
) -> list[dict[str, str]]:
    """Build the message list to send to the LLM."""
    style_instruction = _STYLE_INSTRUCTIONS.get(style, _STYLE_INSTRUCTIONS["concise"])
    lang_note = f" Respond in language: {language}." if language != "en" else ""

    user_content = (
        f"{style_instruction}{lang_note}\n\n"
        f"Text to summarize:\n\n{text}"
    )

    return [
        {"role": "system", "content": _DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _chunk_text(text: str, provider: "BaseLLMProvider", max_tokens: int) -> list[str]:
    """
    Split text into chunks that fit within max_tokens.

    Uses the provider's token counter for accurate splitting.
    """
    # Simple paragraph-based chunking
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_parts: list[str] = []
    current_count = 0

    for para in paragraphs:
        para_tokens = provider.count_tokens(para)
        if current_count + para_tokens > max_tokens and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = [para]
            current_count = para_tokens
        else:
            current_parts.append(para)
            current_count += para_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks or [text]


def summarize(
    text: str,
    provider: "BaseLLMProvider",
    config: "Config",
) -> str:
    """
    Summarize the given text using the provided LLM provider.

    For documents that exceed max_chunk_tokens, the text is split into chunks,
    each chunk is summarized independently, and the partial summaries are
    combined into a final summary.

    Args:
        text: The text to summarize.
        provider: An instantiated BaseLLMProvider.
        config: Application configuration.

    Returns:
        The summary string.

    Raises:
        SummarizerError: If summarization fails.
    """
    total_tokens = provider.count_tokens(text)

    try:
        if total_tokens <= config.max_chunk_tokens:
            # Single-shot summarization
            messages = _build_messages(text, config.style, config.language)
            return provider.complete(
                messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        # Multi-chunk summarization
        chunks = _chunk_text(text, provider, config.max_chunk_tokens)
        partial_summaries: list[str] = []

        for i, chunk in enumerate(chunks, start=1):
            messages = _build_messages(chunk, config.style, config.language)
            partial = provider.complete(
                messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            partial_summaries.append(f"[Part {i}]\n{partial}")

        # Combine partial summaries
        combined = "\n\n".join(partial_summaries)
        combine_messages = [
            {"role": "system", "content": _DEFAULT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"The following are partial summaries of a longer document. "
                    f"Combine them into a single coherent summary. "
                    f"{_STYLE_INSTRUCTIONS.get(config.style, '')}\n\n{combined}"
                ),
            },
        ]
        return provider.complete(
            combine_messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    except LLMError as exc:
        raise SummarizerError(f"LLM error during summarization: {exc}") from exc
    except Exception as exc:
        raise SummarizerError(f"Unexpected summarization error: {exc}") from exc