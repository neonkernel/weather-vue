"""Prompt templates for different summary styles."""

from __future__ import annotations


_STYLE_INSTRUCTIONS: dict[str, str] = {
    "paragraph": (
        "Write a concise summary in clear prose paragraphs. "
        "Capture the main ideas and key details."
    ),
    "bullet": (
        "Write a summary as a bulleted list. "
        "Each bullet should capture one key point. "
        "Use '- ' to start each bullet."
    ),
    "headline": (
        "Write a single-sentence headline that captures the most important "
        "point of the text, followed by a one-paragraph summary."
    ),
    "tldr": (
        "Write a TL;DR (Too Long; Didn't Read) summary in one or two sentences."
    ),
}

_DEFAULT_STYLE = "paragraph"
_DEFAULT_MAX_LENGTH = 500


def build_prompt(
    text: str,
    style: str = _DEFAULT_STYLE,
    max_length: int = _DEFAULT_MAX_LENGTH,
) -> list[dict[str, str]]:
    """Build the messages list for the LLM based on *style* and *max_length*."""
    style_instruction = _STYLE_INSTRUCTIONS.get(style, _STYLE_INSTRUCTIONS[_DEFAULT_STYLE])

    system_message = (
        "You are an expert summarizer. "
        "Your task is to summarize the provided text accurately and concisely. "
        "Do not add information not present in the source text. "
        "Do not include preamble like 'Here is a summary'; output only the summary itself."
    )

    user_message = (
        f"{style_instruction}\n\n"
        f"Keep the summary to approximately {max_length} words or fewer.\n\n"
        f"Text to summarize:\n\n{text}"
    )

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]