"""Reads local .txt and .html files for article ingestion."""

import os
from pathlib import Path
from src.summarizer.models import Article, SourceType
from src.summarizer.exceptions import FetchError, ParseError
from src.summarizer.ingestion.extractor import extract_article, normalize_text

SUPPORTED_EXTENSIONS = {".txt", ".html", ".htm"}
DEFAULT_ENCODING = "utf-8"
FALLBACK_ENCODINGS = ["latin-1", "cp1252", "iso-8859-1"]


def read_file(file_path: str) -> Article:
    """
    Read an article from a local file (.txt or .html).

    Args:
        file_path: Path to a local .txt or .html file

    Returns:
        Article dataclass with extracted content

    Raises:
        FetchError: If the file does not exist or cannot be read
        ParseError: If the file content cannot be parsed
    """
    path = Path(file_path)

    # Validate existence
    if not path.exists():
        raise FetchError(
            f"File not found: '{file_path}'",
            url=file_path,
        )

    if not path.is_file():
        raise FetchError(
            f"Path is not a file: '{file_path}'",
            url=file_path,
        )

    # Validate extension
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ParseError(
            f"Unsupported file extension '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            source=file_path,
        )

    # Read file content with encoding detection
    content = _read_with_encoding(path)

    if not content or not content.strip():
        raise ParseError(
            f"File is empty or contains only whitespace: '{file_path}'",
            source=file_path,
        )

    # Process based on file type
    if ext in (".html", ".htm"):
        article = extract_article(content, url=f"file://{path.resolve()}")
        article.url = str(path.resolve())
        article.source_type = SourceType.FILE
        return article
    else:
        # Plain text file
        text = normalize_text(content)
        if not text:
            raise ParseError(
                f"No meaningful text found in '{file_path}'",
                source=file_path,
            )

        title = _extract_title_from_txt(text)

        return Article(
            title=title,
            text=text,
            url=str(path.resolve()),
            word_count=len(text.split()),
            source_type=SourceType.FILE,
        )


def _read_with_encoding(path: Path) -> str:
    """
    Read a file trying UTF-8 first, then fallback encodings.

    Returns:
        File contents as a string

    Raises:
        FetchError: If the file cannot be read with any supported encoding
    """
    # Try UTF-8 first (with BOM support)
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        pass

    # Try fallback encodings
    for encoding in FALLBACK_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, LookupError):
            continue

    # Last resort: read as bytes and decode with replacement
    try:
        raw = path.read_bytes()
        return raw.decode("utf-8", errors="replace")
    except OSError as e:
        raise FetchError(
            f"Could not read file '{path}': {e}",
            url=str(path),
        ) from e


def _extract_title_from_txt(text: str) -> str:
    """
    Attempt to extract a title from plain text.
    Uses the first non-empty line, truncated to a reasonable length.
    """
    lines = text.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) >= 3:
            # Truncate if too long
            if len(stripped) > 100:
                return stripped[:100].rsplit(" ", 1)[0] + "…"
            return stripped
    return "Untitled Article"