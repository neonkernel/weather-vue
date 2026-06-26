"""Data models for the summarizer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Summary:
    """Represents a generated summary with associated metadata."""

    body: str
    title: Optional[str] = None
    source_url: Optional[str] = None
    model: Optional[str] = None
    style: Optional[str] = None
    word_count: Optional[int] = None
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Auto-compute word count from body if not provided."""
        if self.word_count is None and self.body:
            self.word_count = len(self.body.split())