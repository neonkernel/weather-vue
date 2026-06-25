"""Data models for the summarizer package."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Article:
    """Represents an article to be summarized.

    Attributes:
        text: The full article text.
        title: Optional article title.
        url: Optional source URL.
        author: Optional author name.
        published_at: Optional publication date.
    """

    text: str
    title: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None


@dataclass
class Summary:
    """Represents a generated summary.

    Attributes:
        text: The summary text.
        article_title: Title of the summarized article.
        style: The summary style used.
        model: The model used to generate the summary.
        was_chunked: Whether the article was split into chunks.
        chunk_count: Number of chunks (1 if not chunked).
        prompt_tokens: Total prompt tokens used.
        completion_tokens: Total completion tokens used.
        total_tokens: Total tokens used.
        estimated_cost_usd: Estimated cost in USD.
        created_at: When the summary was created.
    """

    text: str
    article_title: Optional[str] = None
    style: str = "concise"
    model: str = "gpt-4o-mini"
    was_chunked: bool = False
    chunk_count: int = 1
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)