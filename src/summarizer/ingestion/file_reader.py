"""Reads local .txt and .html files for article ingestion."""

import os
from typing import Tuple

from src.summarizer.exceptions import FetchError, ParseError

SUPPORTED_EXTENSIONS = {".txt", ".html", ".htm"}


def read_file(file_path: str, encoding: str = "utf-8") -> Tuple[str, str, bool]:
    """
    Read a local file and return its content.

    Supports .txt, .html, and .htm files.

    Args:
        file_path: Absolute or relative path to the file.
        encoding: File encoding (default: utf-8).

    Returns:
        A tuple of (content, title, is_html) where:
        - content is the raw file content as a string
        - title is derived from the filename (without extension)
        - is_html indicates whether the content is HTML

    Raises:
        FetchError: If the file does not exist or cannot be read.
        ParseError: If the file extension is unsupported.
    """
    # Normalize and resolve path
    file_path = os.path.normpath(file_path)

    if not os.path.exists(file_path):
        raise FetchError(
            f"File not found: '{file_path}'",
            url=file_path,
        )

    if not os.path.isfile(file_path):
        raise FetchError(
            f"Path is not a file: '{file_path}'",
            url=file_path,
        )

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ParseError(
            f"Unsupported file extension '{ext}'. Supported types: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            source=file_path,
        )

    # Derive title from filename
    basename = os.path.basename(file_path)
    title = os.path.splitext(basename)[0].replace("_", " ").replace("-", " ").title()

    # Read file content with UTF-8 default, fallback to latin-1
    try:
        with open(file_path, "r", encoding=encoding, errors="strict") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1, which can decode any byte sequence
        try:
            with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            raise FetchError(
                f"Could not read file '{file_path}': {exc}",
                url=file_path,
            )
    except OSError as exc:
        raise FetchError(
            f"Could not read file '{file_path}': {exc}",
            url=file_path,
        )

    if not content.strip():
        raise ParseError(
            f"File is empty or contains only whitespace: '{file_path}'",
            source=file_path,
        )

    is_html = ext in {".html", ".htm"}
    return content, title, is_html