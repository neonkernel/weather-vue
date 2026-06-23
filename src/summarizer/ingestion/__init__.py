"""Article ingestion package.

Public API:
    fetch_article(source: str) -> Article
        Fetches and parses an article from a URL or local file path.
        Raises FetchError or ParseError on failure.
"""

from src.summarizer.ingestion._pipeline import fetch_article

__all__ = ["fetch_article"]