"""Domain models for the summarizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Article:
    """Represents an article fetched from a URL."""

    url: str
    title: str = ""
    content: str = ""
    html: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass
class Summary:
    """Represents the result of a summarization operation."""

    url: str
    summary: str
    title: str = ""
    model: str = "gpt-4o-mini"
    style: str = "concise"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens