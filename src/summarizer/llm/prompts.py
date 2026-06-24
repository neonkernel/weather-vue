"""PromptBuilder: constructs system + user messages for summarization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class SummaryStyle(str, Enum):
    """Supported summary styles."""

    CONCISE = "concise"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    EXECUTIVE = "executive"


STYLE_INSTRUCTIONS: dict[SummaryStyle, str] = {
    SummaryStyle.CONCISE: (
        "Produce a concise summary in 2-3 sentences. "
        "Capture the core message without unnecessary detail."
    ),
    SummaryStyle.DETAILED: (
        "Produce a detailed summary covering the main points, key arguments, "
        "and important details. Aim for 1-2 paragraphs."
    ),
    SummaryStyle.BULLET_POINTS: (
        "Produce a summary as a bulleted list of the key points. "
        "Use between 3 and 7 bullet points. Start each bullet with '- '."
    ),
    SummaryStyle.EXECUTIVE: (
        "Produce an executive summary suitable for a busy decision-maker. "
        "Include: the main topic, key findings or events, and implications or "
        "next steps if present. Keep it to 3-5 sentences."
    ),
}

SYSTEM_PROMPT_TEMPLATE = (
    "You are an expert summarization assistant. "
    "Your task is to read the provided article text and produce a high-quality summary. "
    "Follow these rules strictly:\n"
    "1. Only use information present in the article — do not add external knowledge.\n"
    "2. Maintain a neutral, objective tone.\n"
    "3. Do not include meta-commentary like 'This article discusses...'.\n"
    "4. Output only the summary — no preamble or explanation.\n"
    "{style_instruction}"
)

CHUNK_SYSTEM_PROMPT = (
    "You are an expert summarization assistant. "
    "You will be given a segment of a longer article. "
    "Summarize only this segment, capturing its key information. "
    "Be concise but thorough. Output only the summary text."
)

REDUCE_SYSTEM_PROMPT = (
    "You are an expert summarization assistant. "
    "You will be given several partial summaries of different segments of a single article. "
    "Combine them into one coherent, unified summary. "
    "Remove redundancy, preserve all key information, and ensure the result reads naturally. "
    "Output only the final combined summary."
)

USER_PROMPT_TEMPLATE = (
    "Article text:\n"
    "'''\n"
    "{article_text}\n"
    "'''\n\n"
    "{instruction}"
)

CHUNK_USER_PROMPT_TEMPLATE = (
    "Article segment ({chunk_index} of {total_chunks}):\n"
    "'''\n"
    "{chunk_text}\n"
    "'''\n\n"
    "Summarize this segment."
)

REDUCE_USER_PROMPT_TEMPLATE = (
    "Partial summaries:\n"
    "'''\n"
    "{partial_summaries}\n"
    "'''\n\n"
    "Produce a single, unified summary from the partial summaries above."
)


@dataclass
class Message:
    """A single chat message."""

    role: str  # "system" or "user" or "assistant"
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class PromptBuilder:
    """Constructs chat messages for summarization tasks."""

    style: SummaryStyle = SummaryStyle.CONCISE

    def build_direct_messages(self, article_text: str) -> List[Message]:
        """Build messages for a single-shot summarization."""
        style_instruction = STYLE_INSTRUCTIONS[self.style]
        system_content = SYSTEM_PROMPT_TEMPLATE.format(
            style_instruction=style_instruction
        )
        user_content = USER_PROMPT_TEMPLATE.format(
            article_text=article_text,
            instruction=style_instruction,
        )
        return [
            Message(role="system", content=system_content),
            Message(role="user", content=user_content),
        ]

    def build_chunk_messages(
        self, chunk_text: str, chunk_index: int, total_chunks: int
    ) -> List[Message]:
        """Build messages for summarizing a single chunk."""
        user_content = CHUNK_USER_PROMPT_TEMPLATE.format(
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_text=chunk_text,
        )
        return [
            Message(role="system", content=CHUNK_SYSTEM_PROMPT),
            Message(role="user", content=user_content),
        ]

    def build_reduce_messages(self, partial_summaries: List[str]) -> List[Message]:
        """Build messages for the reduce step (combining partial summaries)."""
        combined = "\n\n---\n\n".join(
            f"[Summary {i + 1}]\n{s}" for i, s in enumerate(partial_summaries)
        )
        user_content = REDUCE_USER_PROMPT_TEMPLATE.format(
            partial_summaries=combined
        )
        return [
            Message(role="system", content=REDUCE_SYSTEM_PROMPT),
            Message(role="user", content=user_content),
        ]