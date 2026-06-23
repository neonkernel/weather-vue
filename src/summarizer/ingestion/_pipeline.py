"""Top-level pipeline that routes sources to the correct ingestion strategy."""

import os

from src.summarizer.exceptions import FetchError, ParseError
from src.summarizer.models import Article, SourceType
from src.summarizer.ingestion.fetcher import fetch_url
from src.summarizer.ingestion.extractor import extract_text_from_html
from src.summarizer.ingestion.file_reader import read_file


def fetch_article(source: str) -> Article:
    """Fetch and parse an article from a URL or local file.

    Args:
        source: A URL (http/https) or a local file path (.txt or .html).

    Returns:
        An Article dataclass populated with title, text, url, word_count,
        and source_type.

    Raises:
        FetchError: If the content cannot be retrieved.
        ParseError: If the content cannot be parsed into readable text.
    """
    source = source.strip()

    if source.startswith("http://") or source.startswith("https://"):
        return _fetch_from_url(source)
    else:
        return _fetch_from_file(source)


def _fetch_from_url(url: str) -> Article:
    """Fetch an article from an HTTP/HTTPS URL."""
    html, final_url = fetch_url(url)

    title, text = extract_text_from_html(html, url=final_url)

    if not text or len(text.strip()) < 50:
        raise ParseError(
            f"Extracted text is too short or empty for URL: {final_url}",
            source=final_url,
        )

    return Article(
        title=title,
        text=text,
        url=final_url,
        source_type=SourceType.URL,
    )


def _fetch_from_file(path: str) -> Article:
    """Fetch an article from a local file."""
    title, text, file_url = read_file(path)

    ext = os.path.splitext(path)[1].lower()
    if ext == ".html":
        title, text = extract_text_from_html(text, url=file_url)

    if not text or len(text.strip()) < 10:
        raise ParseError(
            f"File content is too short or empty: {path}",
            source=path,
        )

    return Article(
        title=title,
        text=text,
        url=file_url,
        source_type=SourceType.FILE,
    )