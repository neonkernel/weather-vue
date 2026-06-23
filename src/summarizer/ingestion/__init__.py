"""Article ingestion package — URL fetching and local file reading."""

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
        FetchError: If the source cannot be retrieved.
        ParseError: If the content cannot be parsed into readable text.
    """
    if source.startswith("http://") or source.startswith("https://"):
        html_content, final_url = fetch_url(source)
        article = extract_article(html_content, url=final_url)
        article.source_type = SourceType.URL
        return article
    else:
        # Treat as local file
        content, file_type = read_file(source)
        if file_type == "html":
            article = extract_article(content, url=None)
        else:
            # Plain text — minimal processing
            from src.summarizer.ingestion.extractor import normalize_text
            text = normalize_text(content)
            if not text:
                raise ParseError("File contains no readable text.")
            # Derive a simple title from the filename
            title = os.path.splitext(os.path.basename(source))[0].replace("_", " ").replace("-", " ").title()
            article = Article.from_text(text=text, title=title, url=None, source_type=SourceType.FILE)
        article.source_type = SourceType.FILE
        return article


__all__ = ["fetch_article", "fetch_url", "read_file", "extract_article"]