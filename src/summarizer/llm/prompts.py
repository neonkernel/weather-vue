"""PromptBuilder: constructs system and user messages for summarization."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SummaryStyle(str, Enum):
    """Supported summary styles."""

    CONCISE = "concise"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    EXECUTIVE = "executive"


# System prompt templates keyed by style
_SYSTEM_PROMPTS: dict[SummaryStyle, str] = {
    SummaryStyle.CONCISE: (
        "You are an expert summarization assistant. "
        "Your task is to produce clear, accurate, and concise summaries of articles. "
        "Focus on the key facts and main conclusions. "
        "Write in plain English. Avoid unnecessary filler phrases. "
        "Output only the summary — no preamble, no meta-commentary."
    ),
    SummaryStyle.DETAILED: (
        "You are an expert summarization assistant. "
        "Your task is to produce comprehensive summaries that capture all important "
        "details, arguments, evidence, and conclusions from the provided article. "
        "Preserve nuance and supporting data where relevant. "
        "Write in clear, well-structured prose. "
        "Output only the summary — no preamble, no meta-commentary."
    ),
    SummaryStyle.BULLET_POINTS: (
        "You are an expert summarization assistant. "
        "Your task is to extract and present the key points of an article as a "
        "well-organized bullet-point list. "
        "Each bullet should capture one distinct fact, argument, or conclusion. "
        "Use concise, clear language. "
        "Output only the bullet-point list — no preamble, no meta-commentary."
    ),
    SummaryStyle.EXECUTIVE: (
        "You are an expert summarization assistant specializing in executive briefings. "
        "Produce a structured summary with the following sections:\n"
        "1. **Key Takeaway** (1-2 sentences)\n"
        "2. **Context** (2-3 sentences)\n"
        "3. **Key Points** (3-5 bullet points)\n"
        "4. **Implications** (1-2 sentences)\n"
        "Write in professional, concise language suitable for senior decision-makers. "
        "Output only the structured summary — no preamble, no meta-commentary."
    ),
}

# User prompt templates
_USER_PROMPT_TEMPLATE = (
    "Please summarize the following article:\n\n"
    "---\n"
    "{text}\n"
    "---\n\n"
    "Provide a {style_instruction} summary."
)

_CHUNK_USER_PROMPT_TEMPLATE = (
    "This is part {chunk_index} of {total_chunks} of a longer article. "
    "Please summarize this section:\n\n"
    "---\n"
    "{text}\n"
    "---\n\n"
    "Provide a {style_instruction} summary of this section."
)

_MERGE_USER_PROMPT_TEMPLATE = (
    "Below are summaries of individual sections of a longer article. "
    "Please synthesize them into a single coherent summary:\n\n"
    "---\n"
    "{text}\n"
    "---\n\n"
    "Provide a {style_instruction} unified summary."
)

_STYLE_INSTRUCTIONS: dict[SummaryStyle, str] = {
    SummaryStyle.CONCISE: "concise",
    SummaryStyle.DETAILED: "detailed",
    SummaryStyle.BULLET_POINTS: "bullet-point",
    SummaryStyle.EXECUTIVE: "executive-style structured",
}


@dataclass
class PromptBuilder:
    """
    Builds system + user message lists for the OpenAI chat completions API.

    Args:
        style: The desired summary style (default: CONCISE).
        custom_system_prompt: Override the default system prompt entirely.
    """

    style: SummaryStyle = SummaryStyle.CONCISE
    custom_system_prompt: Optional[str] = None

    def _system_prompt(self) -> str:
        if self.custom_system_prompt:
            return self.custom_system_prompt
        return _SYSTEM_PROMPTS[self.style]

    def _style_instruction(self) -> str:
        return _STYLE_INSTRUCTIONS.get(self.style, "concise")

    def build(self, text: str) -> list[dict[str, str]]:
        """
        Build messages for a single-pass summarization.

        Args:
            text: The full article text.

        Returns:
            A list of message dicts suitable for the OpenAI chat API.
        """
        return [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "user",
                "content": _USER_PROMPT_TEMPLATE.format(
                    text=text,
                    style_instruction=self._style_instruction(),
                ),
            },
        ]

    def build_chunk(
        self, text: str, chunk_index: int, total_chunks: int
    ) -> list[dict[str, str]]:
        """
        Build messages for summarizing a single chunk of a larger article.

        Args:
            text: The chunk text.
            chunk_index: 1-based index of this chunk.
            total_chunks: Total number of chunks.

        Returns:
            A list of message dicts suitable for the OpenAI chat API.
        """
        return [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "user",
                "content": _CHUNK_USER_PROMPT_TEMPLATE.format(
                    text=text,
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                    style_instruction=self._style_instruction(),
                ),
            },
        ]

    def build_merge(self, chunk_summaries: list[str]) -> list[dict[str, str]]:
        """
        Build messages to merge multiple chunk summaries into one.

        Args:
            chunk_summaries: List of summary strings (one per chunk).

        Returns:
            A list of message dicts suitable for the OpenAI chat API.
        """
        combined = "\n\n".join(
            f"[Section {i + 1}]\n{s}" for i, s in enumerate(chunk_summaries)
        )
        return [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "user",
                "content": _MERGE_USER_PROMPT_TEMPLATE.format(
                    text=combined,
                    style_instruction=self._style_instruction(),
                ),
            },
        ]