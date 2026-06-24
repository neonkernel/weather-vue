"""Data models for the summarizer."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    """Represents an article to be summarized.

    Attributes:
        content: The full text content of the article.
        title: Optional title of the article.
        url: Optional source URL.
        author: Optional author name.
    """
    content: str
    title: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None


@dataclass
class Summary:
    """Represents a generated summary.

    Attributes:
        summary_text: The generated summary text.
        article_title: The title of the summarized article.
        model: The model used to generate the summary.
        style: The summary style used.
        method: Summarization method used ('direct' or 'map_reduce').
        input_tokens: Number of prompt tokens used.
        output_tokens: Number of completion tokens used.
        estimated_cost_usd: Estimated cost in USD.
    """
    summary_text: str
    article_title: Optional[str] = None
    model: str = "gpt-4o-mini"
    style: str = "concise"
    method: str = "direct"
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0