"""Data models for the summarizer."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Article:
    """Represents a scraped or ingested article."""

    text: str
    title: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    source: Optional[str] = None


@dataclass
class Summary:
    """Represents the output of the summarization pipeline."""

    article_title: str
    article_url: str
    summary_text: str
    model: str
    style: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    strategy: str  # "single-pass" or "map-reduce"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))