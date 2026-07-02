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
    summary_text: str
    style: str = "default"
    tokens_used: int = 0
    model: str = ""
    cost_estimate: float = 0.0


@dataclass
class BatchResult:
    """Result of processing a single item in a batch."""
    source: str
    article: Optional[Article] = None
    summary: Optional[Summary] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    dry_run: bool = False

    @property
    def success(self) -> bool:
        """Whether the item was processed successfully."""
        return self.error is None

    @property
    def summary_text(self) -> Optional[str]:
        """Convenience accessor for summary text."""
        if self.summary:
            return self.summary.summary_text
        return None