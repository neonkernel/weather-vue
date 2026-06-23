"""Shared dataclasses for the summarizer pipeline."""

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
    word_count: int = 0
    compression_ratio: float = 0.0

    def __post_init__(self):
        if self.word_count == 0 and self.summary_text:
            self.word_count = len(self.summary_text.split())
        if self.compression_ratio == 0.0 and self.article.word_count > 0:
            self.compression_ratio = self.word_count / self.article.word_count