"""Data models for the summarizer."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Article:
    """Represents a fetched article."""
    url: str
    title: str
    content: str
    word_count: int = 0
    source: str = ""


@dataclass
class Summary:
    """Represents a generated summary."""
    article: Article
    text: str
    style: str
    model: str
    tokens_used: int = 0
    cost_estimate: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BatchResult:
    """Represents the result of processing a single item in a batch."""
    source: str
    article: Optional[Article] = None
    summary: Optional[Summary] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    success: bool = False
    dry_run: bool = False

    def __post_init__(self):
        if self.summary is not None and not self.error:
            self.success = True
        if self.dry_run and self.article is not None and not self.error:
            self.success = True