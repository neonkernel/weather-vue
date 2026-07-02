"""Data models for the summarizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    """Represents a fetched and parsed article."""

    url: str
    title: str
    text: str
    word_count: int = 0
    source_type: str = "url"  # "url" | "file" | "html"


@dataclass
class Summary:
    """Represents an AI-generated summary of an article."""

    text: str
    style: str = "default"
    model: str = ""
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    dry_run: bool = False


@dataclass
class BatchResult:
    """Result of processing a single source in a batch operation."""

    source: str
    article: Optional[Article]
    summary: Optional[Summary]
    error: Optional[str]
    duration_seconds: float
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None

    @property
    def success(self) -> bool:
        """Return True if the batch item was processed successfully."""
        return self.error is None

    @property
    def title(self) -> str:
        """Return article title or a truncated source identifier."""
        if self.article and self.article.title:
            return self.article.title
        # Truncate long URLs/paths for display
        if len(self.source) > 60:
            return "..." + self.source[-57:]
        return self.source