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
    fetch_duration_seconds: float = 0.0


@dataclass
class Summary:
    """Represents a generated summary."""
    text: str
    style: str
    model: str
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_seconds: float = 0.0


@dataclass
class BatchResult:
    """Represents the result of processing a single item in a batch."""
    source: str  # URL or file path
    article: Optional[Article] = None
    summary: Optional[Summary] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_used: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def success(self) -> bool:
        return self.error is None and self.summary is not None

    @property
    def dry_run_success(self) -> bool:
        """For dry-run mode: success means article was fetched without error."""
        return self.error is None and self.article is not None