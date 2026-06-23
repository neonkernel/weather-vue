"""Local file reading for article ingestion."""

from __future__ import annotations

import logging
import os
from typing import Tuple

from src.summarizer.exceptions import FetchError, ParseError

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".txt", ".html", ".htm"}
_DEFAULT_ENCODING = "utf-8"
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def read_file(path: str, encoding: str = _DEFAULT_ENCODING) -> Tuple[str, str, str]:
    """Read a local file and return its content.

    Supports .txt and .html/.htm files. For .html files, the raw HTML is
    returned and should be passed to the extractor. For .txt files, the
    content is returned as-is.

    Args:
        path: Absolute or relative path to the file.
        encoding: File encoding (defaults to UTF-8).

    Returns:
        A tuple of (title, content, file_uri) where:
            - title is the filename without extension
            - content is the raw file content string
            - file_uri is a file:// URI string

    Raises:
        FetchError: If the file does not exist, is not readable, is too large,
            or has an unsupported extension.
        ParseError: If the file content cannot be decoded.
    """
    path = os.path.abspath(path)
    file_uri = f"file://{path}"
    title = os.path.splitext(os.path.basename(path))[0]

    # Check existence
    if not os.path.exists(path):
        raise FetchError(
            f"File not found: {path}",
            source=file_uri,
        )

    # Check it's a regular file (not a directory)
    if not os.path.isfile(path):
        raise FetchError(
            f"Path is not a regular file: {path}",
            source=file_uri,
        )

    # Check extension
    ext = os.path.splitext(path)[1].lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise FetchError(
            f"Unsupported file extension '{ext}'. Supported: "
            f"{', '.join(sorted(_SUPPORTED_EXTENSIONS))}",
            source=file_uri,
        )

    # Check file size
    file_size = os.path.getsize(path)
    if file_size > _MAX_FILE_SIZE:
        raise FetchError(
            f"File too large ({file_size} bytes, max {_MAX_FILE_SIZE}): {path}",
            source=file_uri,
        )

    # Read content
    logger.info("Reading file: %s (%d bytes)", path, file_size)
    try:
        with open(path, "r", encoding=encoding, errors="strict") as fh:
            content = fh.read()
    except UnicodeDecodeError as exc:
        # Retry with latin-1 as a fallback (lossless)
        logger.warning(
            "UTF-8 decode failed for %s; retrying with latin-1: %s", path, exc
        )
        try:
            with open(path, "r", encoding="latin-1", errors="replace") as fh:
                content = fh.read()
        except Exception as retry_exc:
            raise ParseError(
                f"Could not decode file with UTF-8 or latin-1: {path}",
                source=file_uri,
                cause=retry_exc,
            ) from retry_exc
    except OSError as exc:
        raise FetchError(
            f"Could not read file: {path}",
            source=file_uri,
            cause=exc,
        ) from exc

    if not content.strip():
        raise ParseError(
            f"File is empty or contains only whitespace: {path}",
            source=file_uri,
        )

    return title, content, file_uri