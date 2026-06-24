"""PromptBuilder: constructs system and user prompts for summarization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SummaryStyle(str, Enum):
    """Available summary styles."""

    CONCISE = "concise"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    EXECUTIVE = "executive"


STYLE_INSTRUCTIONS: dict[SummaryStyle, str] = {
    SummaryStyle.CONCISE: (
        "Provide a concise summary in 2-3 sentences that captures the most "
        "important information."
    ),
    SummaryStyle.DETAILED: (
        "Provide a detailed summary covering all major points, key arguments, "
        "and important details. Use 1-3 paragraphs."
    ),
    SummaryStyle.BULLET_POINTS: (
        "Summarize the content as a structured list of bullet points. "
        "Each bullet should capture one key idea or fact."
    ),
    SummaryStyle.EXECUTIVE: (
        "Write an executive summary suitable for a busy professional. "
        "Include: the main topic, key findings or arguments, and any actionable "
        "takeaways. Use clear, professional language."
    ),
}

SYSTEM_PROMPT_TEMPLATE = """You are an expert content summarizer. Your task is to \
summarize articles and text content accurately and faithfully.

Guidelines:
- Only summarize information present in the provided text; do not add external knowledge
- Preserve the original meaning and intent of the content
- Use clear, readable language
- Do not include opinions or editorial commentary unless present in the original
- If the text is a partial chunk of a larger document, summarize only what is provided

{style_instruction}"""

USER_PROMPT_TEMPLATE = """Please summarize the following article:

Title: {title}

Content:
{content}

{instruction}"""

CHUNK_SYSTEM_PROMPT = """You are an expert content summarizer. Your task is to \
summarize a section of a larger article accurately and faithfully.

Guidelines:
- Only summarize information present in the provided text
- This is a partial section — summarize what you see, not what might come before or after
- Use clear, readable language
- Be faithful to the source material"""

CHUNK_USER_PROMPT_TEMPLATE = """Please summarize the following section of an article:

{content}

Provide a concise summary of this section in 2-4 sentences."""

REDUCE_SYSTEM_PROMPT = """You are an expert content synthesizer. Your task is to \
combine multiple section summaries of a single article into one coherent summary.

Guidelines:
- Synthesize the section summaries into a unified, flowing summary
- Eliminate redundancy while preserving all important information
- Maintain logical flow and coherence
- Do not add information not present in the section summaries"""

REDUCE_USER_PROMPT_TEMPLATE = """The following are summaries of consecutive sections \
of an article titled "{title}".

Please combine them into a single, coherent summary:

{section_summaries}

{instruction}"""


@dataclass
class PromptBuilder:
    """Builds system and user prompts for summarization tasks."""

    style: SummaryStyle = SummaryStyle.CONCISE
    custom_instruction: Optional[str] = None

    def _get_style_instruction(self) -> str:
        return STYLE_INSTRUCTIONS.get(self.style, STYLE_INSTRUCTIONS[SummaryStyle.CONCISE])

    def _get_user_instruction(self) -> str:
        if self.custom_instruction:
            return self.custom_instruction
        return self._get_style_instruction()

    def build_system_prompt(self) -> str:
        """Build the system prompt for direct summarization.

        Returns:
            The system prompt string.
        """
        style_instruction = self._get_style_instruction()
        return SYSTEM_PROMPT_TEMPLATE.format(style_instruction=style_instruction)

    def build_user_prompt(self, content: str, title: str = "") -> str:
        """Build the user prompt for direct summarization.

        Args:
            content: The article content to summarize.
            title: Optional article title.

        Returns:
            The user prompt string.
        """
        instruction = self._get_user_instruction()
        return USER_PROMPT_TEMPLATE.format(
            title=title or "Untitled",
            content=content,
            instruction=instruction,
        )

    def build_messages(
        self, content: str, title: str = ""
    ) -> list[dict[str, str]]:
        """Build the full messages list for a direct summarization call.

        Args:
            content: The article content to summarize.
            title: Optional article title.

        Returns:
            A list of message dicts with 'role' and 'content' keys.
        """
        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": self.build_user_prompt(content, title)},
        ]

    def build_chunk_messages(self, chunk_text: str) -> list[dict[str, str]]:
        """Build messages for summarizing a single chunk.

        Args:
            chunk_text: The text chunk to summarize.

        Returns:
            A list of message dicts.
        """
        return [
            {"role": "system", "content": CHUNK_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": CHUNK_USER_PROMPT_TEMPLATE.format(content=chunk_text),
            },
        ]

    def build_reduce_messages(
        self, section_summaries: list[str], title: str = ""
    ) -> list[dict[str, str]]:
        """Build messages for the reduce step (combining chunk summaries).

        Args:
            section_summaries: List of summaries from each chunk.
            title: Optional article title.

        Returns:
            A list of message dicts.
        """
        formatted_summaries = "\n\n".join(
            f"Section {i + 1}:\n{summary}"
            for i, summary in enumerate(section_summaries)
        )
        instruction = self._get_user_instruction()
        return [
            {"role": "system", "content": REDUCE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": REDUCE_USER_PROMPT_TEMPLATE.format(
                    title=title or "Untitled",
                    section_summaries=formatted_summaries,
                    instruction=instruction,
                ),
            },
        ]