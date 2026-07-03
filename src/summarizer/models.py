"""Data models for the summarizer."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    """Represents a fetched article."""
    url: str
    title: str
    content: str
    source: str = ""
    word_count: int = 0

    def __post_init__(self):
        if self.word_count == 0 and self.content:
            self.word_count = len(self.content.split())


@dataclass
class Summary:
    """Represents a generated summary."""
    article: Article
    text: str
    style: str = "default"
    model: str = ""
    tokens_used: int = 0
    cost_estimate: float = 0.0
    duration_seconds: float = 0.0


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

    def __post_init__(self):
        if self.summary is not None and self.error is None:
            self.success = True
            if self.tokens_used == 0 and self.summary.tokens_used:
                self.tokens_used = self.summary.tokens_used
            if self.cost_estimate == 0.0 and self.summary.cost_estimate:
                self.cost_estimate = self.summary.cost_estimate


@dataclass
class BatchReport:
    """Aggregate report for a batch processing run."""
    results: list[BatchResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def successes(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failures(self) -> int:
        return sum(1 for r in self.results if not r.success)

    @property
    def total_tokens(self) -> int:
        return sum(r.tokens_used for r in self.results)

    @property
    def total_cost(self) -> float:
        return sum(r.cost_estimate for r in self.results)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.successes / self.total) * 100.0