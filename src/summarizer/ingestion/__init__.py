"""Article ingestion package — fetches and parses articles from URLs and local files."""

from src.summarizer.ingestion.fetcher import fetch_url
from src.summarizer.ingestion.extractor import extract_article
from src.summarizer.ingestion.file_reader import read_file
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
        FetchError: If the URL cannot be fetched.
        ParseError: If the content cannot be parsed.
    """
    if source.startswith("http://") or source.startswith("https://"):
        html_content, final_url = fetch_url(source)
        article = extract_article(html_content, url=final_url)
        article.url = final_url
        article.source_type = SourceType.URL
        return article
    else:
        # Treat as a local file path
        text, title, is_html = read_file(source)
        if is_html:
            article = extract_article(text, url=None)
            article.source_type = SourceType.FILE
            if not article.title and title:
                article.title = title
            return article
        else:
            word_count = len(text.split())
            return Article(
                title=title or os.path.basename(source),
                text=text,
                url=None,
                word_count=word_count,
                source_type=SourceType.FILE,
            )


__all__ = ["fetch_article", "fetch_url", "extract_article", "read_file"]