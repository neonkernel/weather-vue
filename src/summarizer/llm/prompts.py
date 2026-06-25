"""PromptBuilder class for constructing LLM prompts."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SummaryStyle(str, Enum):
    """Available summary styles."""
    CONCISE = "concise"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    EXECUTIVE = "executive"


SYSTEM_PROMPTS = {
    SummaryStyle.CONCISE: (
        "You are a precise summarization assistant. Your task is to create clear, "
        "concise summaries of articles. Focus on the most important information, "
        "eliminate redundancy, and maintain factual accuracy. Keep summaries brief "
        "but informative, capturing the core message in a few sentences."
    ),
    SummaryStyle.DETAILED: (
        "You are a thorough summarization assistant. Your task is to create comprehensive "
        "summaries of articles that capture all key points, supporting details, and context. "
        "Maintain the logical flow of the original content while making it more digestible. "
        "Ensure no important information is omitted."
    ),
    SummaryStyle.BULLET_POINTS: (
        "You are a structured summarization assistant. Your task is to distill articles "
        "into clear, actionable bullet points. Each bullet should represent a distinct, "
        "important piece of information. Use concise language and parallel structure. "
        "Aim for 5-10 bullet points that capture the essential content."
    ),
    SummaryStyle.EXECUTIVE: (
        "You are an executive briefing assistant. Your task is to create high-level "
        "summaries suitable for busy executives. Focus on key decisions, outcomes, "
        "implications, and action items. Be direct and results-oriented. "
        "Avoid technical jargon unless essential."
    ),
}

USER_PROMPT_TEMPLATE = """Please summarize the following article:

---
{article_text}
---

{instruction}"""

STYLE_INSTRUCTIONS = {
    SummaryStyle.CONCISE: (
        "Provide a concise summary in 2-4 sentences that captures the main point "
        "and most important supporting details."
    ),
    SummaryStyle.DETAILED: (
        "Provide a detailed summary that covers all key points, important details, "
        "and context. Use clear paragraphs organized by topic."
    ),
    SummaryStyle.BULLET_POINTS: (
        "Provide a bullet-point summary with 5-10 key points. Each bullet should "
        "be a complete thought expressed in 1-2 sentences."
    ),
    SummaryStyle.EXECUTIVE: (
        "Provide an executive summary with: (1) a one-sentence bottom line, "
        "(2) 3-5 key takeaways, and (3) any recommended actions or implications."
    ),
}

CHUNK_SUMMARIZE_INSTRUCTION = (
    "This is a portion of a longer article. Summarize this section, capturing "
    "all key points and important details. Be thorough as this summary will be "
    "used to create a final summary."
)

MERGE_SUMMARIES_SYSTEM_PROMPT = (
    "You are a summarization assistant specializing in synthesizing multiple "
    "section summaries into a coherent final summary. Maintain consistency, "
    "eliminate redundancy, and ensure the final summary flows naturally."
)

MERGE_SUMMARIES_USER_TEMPLATE = """The following are summaries of different sections of an article. 
Please synthesize them into a single, cohesive summary:

---
{combined_summaries}
---

{instruction}"""


@dataclass
class Message:
    """Represents a chat message."""
    role: str
    content: str


class PromptBuilder:
    """
    Constructs prompts for the summarization LLM.

    Supports multiple summary styles and handles both direct summarization
    and chunk-based map-reduce summarization.
    """

    def __init__(self, style: SummaryStyle = SummaryStyle.CONCISE):
        """
        Initialize the PromptBuilder.

        Args:
            style: The summary style to use.
        """
        self.style = style

    def build_messages(self, article_text: str) -> list[dict]:
        """
        Build chat messages for direct article summarization.

        Args:
            article_text: The full article text to summarize.

        Returns:
            A list of message dictionaries for the OpenAI API.
        """
        system_prompt = SYSTEM_PROMPTS[self.style]
        instruction = STYLE_INSTRUCTIONS[self.style]
        user_prompt = USER_PROMPT_TEMPLATE.format(
            article_text=article_text,
            instruction=instruction,
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def build_chunk_messages(self, chunk_text: str, chunk_index: int, total_chunks: int) -> list[dict]:
        """
        Build chat messages for summarizing a single chunk.

        Args:
            chunk_text: The text of the chunk to summarize.
            chunk_index: The 0-based index of this chunk.
            total_chunks: The total number of chunks.

        Returns:
            A list of message dictionaries for the OpenAI API.
        """
        system_prompt = SYSTEM_PROMPTS[SummaryStyle.DETAILED]
        user_prompt = USER_PROMPT_TEMPLATE.format(
            article_text=chunk_text,
            instruction=(
                f"This is section {chunk_index + 1} of {total_chunks}. "
                f"{CHUNK_SUMMARIZE_INSTRUCTION}"
            ),
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def build_merge_messages(self, chunk_summaries: list[str]) -> list[dict]:
        """
        Build chat messages for merging chunk summaries.

        Args:
            chunk_summaries: List of summaries from individual chunks.

        Returns:
            A list of message dictionaries for the OpenAI API.
        """
        combined = "\n\n---\n\n".join(
            f"Section {i + 1}:\n{summary}"
            for i, summary in enumerate(chunk_summaries)
        )
        instruction = STYLE_INSTRUCTIONS[self.style]
        user_prompt = MERGE_SUMMARIES_USER_TEMPLATE.format(
            combined_summaries=combined,
            instruction=instruction,
        )
        return [
            {"role": "system", "content": MERGE_SUMMARIES_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for the current style."""
        return SYSTEM_PROMPTS[self.style]