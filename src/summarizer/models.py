"""Domain models for the summarizer package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    """Represents a fetched and parsed article."""

    url: str
    title: str
    text: str
    html: Optional[str] = None


@dataclass
class Summary:
    """Represents the result of a summarization operation."""

    title: str
    summary: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float = 0.0