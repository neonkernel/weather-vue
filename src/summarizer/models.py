"""Shared dataclasses for the summarizer."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    URL = "url"
    FILE = "file"
    TEXT = "text"


@dataclass
class Article:
    """Represents a fetched and parsed article."""

    title: str
    text: str
    url: Optional[str]
    word_count: int
    source_type: SourceType = SourceType.URL

    @classmethod
    def from_text(cls, text: str, title: str = "", url: Optional[str] = None, source_type: SourceType = SourceType.URL) -> "Article":
        word_count = len(text.split()) if text else 0
        return cls(
            title=title,
            text=text,
            url=url,
            word_count=word_count,
            source_type=source_type,
        )


@dataclass
class Summary:
    """Represents a generated summary."""

    article: Article
    summary_text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    bullet_points: list = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens