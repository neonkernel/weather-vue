"""PromptBuilder: constructs system and user messages for the LLM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SummaryStyle = Literal["concise", "detailed", "bullet"]

SYSTEM_PROMPTS: dict[SummaryStyle, str] = {
    "concise": (
        "You are an expert summarizer. Your task is to produce a clear, concise summary "
        "of the provided article. The summary should:\n"
        "- Capture the most important information\n"
        "- Be written in plain, accessible English\n"
        "- Be 2–4 sentences long\n"
        "- Preserve factual accuracy — do not add information not present in the source\n"
        "- Avoid filler phrases like 'This article discusses…'\n"
        "Respond with only the summary text, no preamble."
    ),
    "detailed": (
        "You are an expert summarizer. Your task is to produce a thorough summary "
        "of the provided article. The summary should:\n"
        "- Cover all key points, arguments, and conclusions\n"
        "- Be written in clear, professional English\n"
        "- Be 1–3 paragraphs long\n"
        "- Preserve factual accuracy — do not add information not present in the source\n"
        "Respond with only the summary text, no preamble."
    ),
    "bullet": (
        "You are an expert summarizer. Your task is to summarize the provided article "
        "as a structured list of bullet points. Each bullet should:\n"
        "- Represent one distinct key point or finding\n"
        "- Be concise (one sentence each)\n"
        "- Begin with a dash (-)\n"
        "- Be factually accurate and grounded in the source text\n"
        "Respond with only the bullet list, no preamble."
    ),
}

CHUNK_SYSTEM_PROMPT = (
    "You are an expert summarizer. You will be given a portion of a longer article. "
    "Summarize this portion, capturing the key points. Be concise but complete — "
    "your summary will later be combined with summaries of other portions. "
    "Respond with only the summary text, no preamble."
)

REDUCE_SYSTEM_PROMPT = (
    "You are an expert summarizer. You will be given a series of partial summaries "
    "of different sections of the same article. Combine these into a single, coherent "
    "summary that covers all the key points without redundancy. "
    "Respond with only the final summary text, no preamble."
)


@dataclass
class PromptBuilder:
    """Builds OpenAI-compatible message lists for summarization tasks."""

    style: SummaryStyle = "concise"
    extra_instructions: str = ""

    def build_messages(self, article_text: str) -> list[dict[str, str]]:
        """Build messages for a direct (single-pass) summarization."""
        system_content = SYSTEM_PROMPTS[self.style]
        if self.extra_instructions:
            system_content += f"\n\nAdditional instructions: {self.extra_instructions}"

        user_content = f"Please summarize the following article:\n\n{article_text}"

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def build_chunk_messages(self, chunk_text: str, chunk_index: int, total_chunks: int) -> list[dict[str, str]]:
        """Build messages for summarizing a single chunk in the map phase."""
        user_content = (
            f"Article section {chunk_index + 1} of {total_chunks}:\n\n{chunk_text}"
        )
        return [
            {"role": "system", "content": CHUNK_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def build_reduce_messages(self, partial_summaries: list[str]) -> list[dict[str, str]]:
        """Build messages for combining chunk summaries in the reduce phase."""
        numbered = "\n\n".join(
            f"Section {i + 1} summary:\n{s}" for i, s in enumerate(partial_summaries)
        )
        user_content = f"Please combine the following partial summaries into one:\n\n{numbered}"
        return [
            {"role": "system", "content": REDUCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]