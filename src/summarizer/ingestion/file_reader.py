"""Local file reading for article ingestion."""

import os
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from src.summarizer.exceptions import FetchError, ParseError
from src.summarizer.ingestion.extractor import extract_article, normalize_text
from src.summarizer.models import Article, SourceType

SUPPORTED_EXTENSIONS = {".txt", ".html", ".htm"}


def read_file(file_path: str, encoding: str = "utf-8") -> Article:
    """
    Read a local file and return an Article.

    Supports .txt and .html/.htm files.

    Args:
        file_path: Path to the local file.
        encoding: File encoding (defaults to UTF-8).

    Returns:
        An Article dataclass with title, text, url (as file path), and word_count.

    Raises:
        FetchError: If the file does not exist or cannot be read.
        ParseError: If the file type is unsupported or content cannot be parsed.
    """
    path = Path(file_path)

    # Validate file existence
    if not path.exists():
        raise FetchError(
            f"File not found: {file_path}",
            url=file_path,
        )

    if not path.is_file():
        raise FetchError(
            f"Path is not a file: {file_path}",
            url=file_path,
        )

    # Validate extension
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ParseError(
            f"Unsupported file type '{extension}'. Supported types: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS)),
            source=file_path,
        )

    # Read the file content
    try:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
    except PermissionError:
        raise FetchError(
            f"Permission denied reading file: {file_path}",
            url=file_path,
        )
    except OSError as e:
        raise FetchError(
            f"OS error reading file '{file_path}': {e}",
            url=file_path,
        )

    if not content.strip():
        raise ParseError(
            f"File is empty: {file_path}",
            source=file_path,
        )

    # Process based on file type
    if extension == ".txt":
        return _process_text_file(content, file_path)
    elif extension in (".html", ".htm"):
        return _process_html_file(content, file_path)

    raise ParseError(f"Unhandled file extension: {extension}", source=file_path)


def _process_text_file(content: str, file_path: str) -> Article:
    """Process a plain text file."""
    text = normalize_text(content)

    if not text or len(text.split()) < 5:
        raise ParseError(
            f"Text file contains insufficient content: {file_path}",
            source=file_path,
        )

    # Use the filename (without extension) as the title
    title = Path(file_path).stem.replace("_", " ").replace("-", " ").title()

    return Article(
        title=title,
        text=text,
        url=file_path,
        word_count=len(text.split()),
        source_type=SourceType.FILE,
    )


def _process_html_file(content: str, file_path: str) -> Article:
    """Process a local HTML file."""
    try:
        article = extract_article(content, url=None)
        article.url = file_path
        article.source_type = SourceType.FILE
        return article
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(
            f"Failed to parse HTML file '{file_path}': {e}",
            source=file_path,
        )