"""Data models for the summarizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    """Represents an article to be summarized."""

    content: str
    title: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("Article content cannot be empty.")


@dataclass
class Summary:
    """Represents a generated summary with metadata."""

    article_title: str
    summary: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    strategy: str = "direct"

    @property
    def total_tokens(self) -> int:
        """Total tokens used (prompt + completion)."""
        return self.prompt_tokens + self.completion_tokens