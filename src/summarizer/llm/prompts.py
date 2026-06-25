"""PromptBuilder class for constructing LLM prompts."""

from dataclasses import dataclass
from typing import Optional


SUMMARY_STYLES = {
    "concise": {
        "description": "a brief, concise summary",
        "instructions": (
            "Provide a clear and concise summary in 2-4 sentences. "
            "Focus on the most important points only."
        ),
    },
    "detailed": {
        "description": "a detailed summary",
        "instructions": (
            "Provide a comprehensive summary covering all major points, "
            "key arguments, and important details. Use paragraphs as needed."
        ),
    },
    "bullet": {
        "description": "a bullet-point summary",
        "instructions": (
            "Provide a summary as a bulleted list of key points. "
            "Each bullet should be a concise, standalone point."
        ),
    },
    "executive": {
        "description": "an executive summary",
        "instructions": (
            "Provide an executive summary suitable for a busy professional. "
            "Include: (1) the main topic/issue, (2) key findings or arguments, "
            "(3) implications or conclusions. Keep it under 200 words."
        ),
    },
}

SYSTEM_PROMPT_TEMPLATE = """You are an expert summarizer. Your task is to read articles and produce high-quality summaries.

Guidelines:
- Be accurate and faithful to the source material
- Do not add information not present in the article
- Do not include personal opinions or external knowledge
- Write in clear, professional English
- Focus on the most important and relevant information
- Maintain the tone and perspective of the original article where appropriate

You will produce {description}."""

CHUNK_SYSTEM_PROMPT = """You are an expert summarizer. Your task is to summarize a section of a larger article.

Guidelines:
- Be accurate and faithful to the source material
- Do not add information not present in the text
- Do not include personal opinions or external knowledge
- Write in clear, professional English
- This is one section of a larger article, so focus on what is covered in this section

Produce a concise summary of this section."""

MERGE_SYSTEM_PROMPT = """You are an expert summarizer. Your task is to synthesize multiple section summaries into a cohesive final summary.

Guidelines:
- Combine the section summaries into a unified, flowing summary
- Eliminate redundancy and repetition
- Maintain logical flow and coherence
- Do not add information not present in the section summaries
- Write in clear, professional English

You will produce {description}."""


@dataclass
class Message:
    """A single message in a conversation."""
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class PromptBuilder:
    """Constructs system and user prompts for summarization tasks.

    Args:
        style: Summary style. One of: 'concise', 'detailed', 'bullet', 'executive'.
    """

    def __init__(self, style: str = "concise"):
        if style not in SUMMARY_STYLES:
            raise ValueError(
                f"Unknown style '{style}'. Valid styles: {list(SUMMARY_STYLES.keys())}"
            )
        self.style = style
        self._style_config = SUMMARY_STYLES[style]

    def build_direct_messages(self, article_text: str, title: Optional[str] = None) -> list[dict]:
        """Build messages for direct (single-pass) summarization.

        Args:
            article_text: The full article text.
            title: Optional article title for context.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        system_message = SYSTEM_PROMPT_TEMPLATE.format(
            description=self._style_config["description"]
        )

        user_parts = []
        if title:
            user_parts.append(f"Article Title: {title}\n")
        user_parts.append("Article Text:")
        user_parts.append(article_text)
        user_parts.append(f"\n{self._style_config['instructions']}")

        user_message = "\n".join(user_parts)

        return [
            Message(role="system", content=system_message).to_dict(),
            Message(role="user", content=user_message).to_dict(),
        ]

    def build_chunk_messages(self, chunk_text: str, chunk_index: int, total_chunks: int) -> list[dict]:
        """Build messages for summarizing a single chunk.

        Args:
            chunk_text: The text of this chunk.
            chunk_index: Zero-based index of this chunk.
            total_chunks: Total number of chunks.

        Returns:
            List of message dicts.
        """
        user_message = (
            f"Section {chunk_index + 1} of {total_chunks}:\n\n"
            f"{chunk_text}\n\n"
            "Please summarize this section concisely."
        )

        return [
            Message(role="system", content=CHUNK_SYSTEM_PROMPT).to_dict(),
            Message(role="user", content=user_message).to_dict(),
        ]

    def build_merge_messages(
        self,
        chunk_summaries: list[str],
        title: Optional[str] = None,
    ) -> list[dict]:
        """Build messages for merging chunk summaries into a final summary.

        Args:
            chunk_summaries: List of summaries for each chunk.
            title: Optional article title for context.

        Returns:
            List of message dicts.
        """
        system_message = MERGE_SYSTEM_PROMPT.format(
            description=self._style_config["description"]
        )

        user_parts = []
        if title:
            user_parts.append(f"Article Title: {title}\n")
        user_parts.append(
            f"Below are summaries of {len(chunk_summaries)} sections of an article. "
            "Please synthesize them into a single cohesive summary.\n"
        )

        for i, summary in enumerate(chunk_summaries, 1):
            user_parts.append(f"Section {i} Summary:\n{summary}")

        user_parts.append(f"\n{self._style_config['instructions']}")

        user_message = "\n\n".join(user_parts)

        return [
            Message(role="system", content=system_message).to_dict(),
            Message(role="user", content=user_message).to_dict(),
        ]