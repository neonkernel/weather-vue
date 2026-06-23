"""Shared dataclasses for the summarizer application."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


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
    source_type: SourceType = SourceType.TEXT

    def __post_init__(self):
        if self.word_count == 0 and self.text:
            self.word_count = len(self.text.split())


@dataclass
class Summary:
    """Represents a generated summary of an article."""
    article: Article
    summary_text: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    bullet_points: list = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens