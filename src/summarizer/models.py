"""Data models for the summarizer."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Article:
    """Represents an article to be summarized."""
    title: str
    content: str
    url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    source: Optional[str] = None


@dataclass
class Summary:
    """Represents the result of a summarization operation."""
    title: str
    summary: str
    style: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    method: str  # "direct" or "map_reduce"
    url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))