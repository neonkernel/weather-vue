"""Shared dataclasses for the summarizer package."""

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
    url: Optional[str] = None
    word_count: int = 0
    source_type: SourceType = SourceType.URL

    def __post_init__(self):
        if self.word_count == 0 and self.text:
            self.word_count = len(self.text.split())


@dataclass
class Summary:
    """Represents a generated summary of an article."""
    article: Article
    summary_text: str
    model: str = ""
    bullet_points: list = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.bullet_points, list) and not self.bullet_points and self.summary_text:
            # Auto-generate bullet points from summary if not provided
            pass