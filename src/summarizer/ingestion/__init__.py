"""Article ingestion package — provides a unified fetch_article interface."""

from src.summarizer.ingestion.fetcher import fetch_url
from src.summarizer.ingestion.file_reader import read_file
from src.summarizer.ingestion.extractor import extract_article
from src.summarizer.models import Article, SourceType
from src.summarizer.exceptions import FetchError, ParseError

import os


def fetch_article(source: str) -> Article:
    """
    Fetch and parse an article from a URL or local file path.

    Args:
        source: A URL (http/https) or a local file path (.txt or .html).

    Returns:
        An Article dataclass with title, text, url, word_count, and source_type.

    Raises:
        FetchError: If the source cannot be retrieved (network errors, HTTP errors).
        ParseError: If the content cannot be parsed or yields no usable text.
    """
    if source.startswith("http://") or source.startswith("https://"):
        html_content, final_url = fetch_url(source)
        article = extract_article(html_content, url=final_url)
        article.source_type = SourceType.URL
        return article
    else:
        # Treat as local file
        article = read_file(source)
        return article


__all__ = ["fetch_article"]