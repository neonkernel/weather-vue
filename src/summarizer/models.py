"""Data models for the summarizer package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ArticleContent:
    """Represents the ingested content of a single article."""

    url: str
    title: str
    text: str
    html: Optional[str] = None
    word_count: int = 0

    def __post_init__(self) -> None:
        if self.word_count == 0 and self.text:
            self.word_count = len(self.text.split())


@dataclass
class SummaryResult:
    """Represents the result of summarising a single article."""

    article: ArticleContent
    summary: str
    tokens_used: int = 0
    model: str = ""
    style: str = "default"
    duration_seconds: float = 0.0


@dataclass
class BatchResult:
    """Represents the result of processing one source in a batch run."""

    source: str
    article: Optional[ArticleContent]
    summary: Optional[str]
    error: Optional[str]
    duration_seconds: float = 0.0
    tokens_used: int = 0

    @property
    def succeeded(self) -> bool:
        """True when the item was processed without error."""
        return self.error is None

    @property
    def title(self) -> str:
        """Article title if available, otherwise the source identifier."""
        if self.article and self.article.title:
            return self.article.title
        return self.source


@dataclass
class BatchReport:
    """Aggregate statistics for a completed batch run."""

    results: list[BatchResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def successes(self) -> int:
        return sum(1 for r in self.results if r.succeeded)

    @property
    def failures(self) -> int:
        return self.total - self.successes

    @property
    def total_tokens(self) -> int:
        return sum(r.tokens_used for r in self.results)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.successes / self.total * 100