"""PromptBuilder class for constructing LLM prompts for article summarization."""

from dataclasses import dataclass, field
from typing import Optional


SUMMARY_STYLES = {
    "concise": (
        "You are an expert summarizer. Your task is to produce clear, concise summaries "
        "that capture the most important information. Be brief and direct."
    ),
    "detailed": (
        "You are an expert summarizer. Your task is to produce comprehensive summaries "
        "that capture all key points, supporting details, and nuances of the content. "
        "Be thorough while remaining organized."
    ),
    "bullet": (
        "You are an expert summarizer. Your task is to produce summaries as structured "
        "bullet points, organizing key information into clear, scannable lists. "
        "Use hierarchical bullets where appropriate."
    ),
    "executive": (
        "You are an expert summarizer for business executives. Produce summaries that "
        "highlight key decisions, outcomes, and actionable insights. Focus on business "
        "impact and strategic relevance."
    ),
}

DEFAULT_STYLE = "concise"


@dataclass
class PromptMessages:
    """Container for system and user prompt messages."""
    system: str
    user: str

    def to_openai_messages(self) -> list[dict]:
        """Convert to OpenAI-compatible message format."""
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
        ]


class PromptBuilder:
    """Builds system and user prompts for article summarization.

    Args:
        style: Summary style — one of 'concise', 'detailed', 'bullet', 'executive'.
        max_summary_words: Optional word limit hint for the summary.
        custom_system_prompt: Override the default system prompt entirely.
    """

    def __init__(
        self,
        style: str = DEFAULT_STYLE,
        max_summary_words: Optional[int] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> None:
        if style not in SUMMARY_STYLES and custom_system_prompt is None:
            raise ValueError(
                f"Unknown style '{style}'. Valid styles: {list(SUMMARY_STYLES.keys())}"
            )
        self.style = style
        self.max_summary_words = max_summary_words
        self.custom_system_prompt = custom_system_prompt

    def build_system_prompt(self) -> str:
        """Build the system prompt based on the configured style."""
        if self.custom_system_prompt:
            return self.custom_system_prompt

        base_prompt = SUMMARY_STYLES.get(self.style, SUMMARY_STYLES[DEFAULT_STYLE])

        constraints = [
            "Always produce factually accurate summaries based solely on the provided text.",
            "Do not add information that is not present in the source material.",
            "Maintain a neutral, objective tone.",
        ]

        if self.max_summary_words:
            constraints.append(
                f"Keep the summary under {self.max_summary_words} words."
            )

        constraint_text = "\n".join(f"- {c}" for c in constraints)
        return f"{base_prompt}\n\nConstraints:\n{constraint_text}"

    def build_user_prompt(self, article_text: str, title: Optional[str] = None) -> str:
        """Build the user prompt for a given article.

        Args:
            article_text: The full text of the article to summarize.
            title: Optional article title to provide context.

        Returns:
            The formatted user prompt string.
        """
        parts = []

        if title:
            parts.append(f"Article Title: {title}\n")

        parts.append("Article Text:")
        parts.append(article_text.strip())
        parts.append("\nPlease provide a summary of the above article.")

        return "\n".join(parts)

    def build_chunk_user_prompt(self, chunk_text: str, chunk_index: int, total_chunks: int) -> str:
        """Build a user prompt for summarizing a single chunk in map-reduce mode.

        Args:
            chunk_text: The text of this chunk.
            chunk_index: 1-based index of this chunk.
            total_chunks: Total number of chunks.

        Returns:
            The formatted user prompt for chunk summarization.
        """
        parts = [
            f"This is part {chunk_index} of {total_chunks} of a longer article.",
            "Please summarize the key points from this section:\n",
            chunk_text.strip(),
            "\nProvide a concise summary of this section.",
        ]
        return "\n".join(parts)

    def build_reduce_user_prompt(self, chunk_summaries: list[str], title: Optional[str] = None) -> str:
        """Build a user prompt for combining chunk summaries in the reduce step.

        Args:
            chunk_summaries: List of summaries from individual chunks.
            title: Optional article title.

        Returns:
            The formatted user prompt for the reduce step.
        """
        parts = []

        if title:
            parts.append(f"Article Title: {title}\n")

        parts.append(
            "Below are summaries of individual sections of a longer article. "
            "Please synthesize these into a single coherent summary:\n"
        )

        for i, summary in enumerate(chunk_summaries, 1):
            parts.append(f"Section {i} Summary:")
            parts.append(summary.strip())
            parts.append("")

        parts.append("Please provide a unified summary that captures all the key points from the sections above.")

        return "\n".join(parts)

    def build(self, article_text: str, title: Optional[str] = None) -> PromptMessages:
        """Build the complete prompt messages for an article.

        Args:
            article_text: The full text of the article.
            title: Optional article title.

        Returns:
            PromptMessages with system and user prompts.
        """
        return PromptMessages(
            system=self.build_system_prompt(),
            user=self.build_user_prompt(article_text, title),
        )