"""Local file reading for .txt and .html files."""

import logging
import os
from typing import Tuple

from src.summarizer.exceptions import FetchError, ParseError

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".html", ".htm"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
DEFAULT_ENCODING = "utf-8"
FALLBACK_ENCODINGS = ["latin-1", "cp1252", "iso-8859-1"]


def read_file(path: str) -> Tuple[str, str]:
    """
    Read a local .txt or .html file and return its content.

    Args:
        path: Absolute or relative path to a .txt or .html file.

    Returns:
        A tuple of (content: str, file_type: str) where file_type is "txt" or "html".

    Raises:
        FetchError: If the file does not exist, is not accessible, or the
                    extension is unsupported.
        ParseError: If the file cannot be decoded.
    """
    # Resolve to an absolute path
    abs_path = os.path.abspath(path)

    # Check existence
    if not os.path.exists(abs_path):
        raise FetchError(f"File not found: '{abs_path}'")

    # Check it's a regular file (not a directory or special file)
    if not os.path.isfile(abs_path):
        raise FetchError(f"Path is not a regular file: '{abs_path}'")

    # Check extension
    _, ext = os.path.splitext(abs_path)
    ext = ext.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise FetchError(
            f"Unsupported file extension: '{ext}'. "
            f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Check file size
    file_size = os.path.getsize(abs_path)
    if file_size == 0:
        raise FetchError(f"File is empty: '{abs_path}'")
    if file_size > MAX_FILE_SIZE:
        raise FetchError(
            f"File too large: {file_size / (1024*1024):.1f} MB "
            f"(max {MAX_FILE_SIZE // (1024*1024)} MB): '{abs_path}'"
        )

    logger.info("Reading file: %s (%d bytes)", abs_path, file_size)

    # Attempt to read with UTF-8, then fallback encodings
    content = None
    tried_encodings = [DEFAULT_ENCODING] + FALLBACK_ENCODINGS

    for encoding in tried_encodings:
        try:
            with open(abs_path, "r", encoding=encoding) as f:
                content = f.read()
            logger.debug("Successfully decoded '%s' with encoding '%s'.", abs_path, encoding)
            break
        except UnicodeDecodeError:
            logger.debug("Failed to decode '%s' with encoding '%s'.", abs_path, encoding)
            continue
        except OSError as e:
            raise FetchError(
                f"Cannot read file '{abs_path}': {e}",
                cause=e,
            )

    if content is None:
        # Last resort: read with errors='replace'
        try:
            with open(abs_path, "r", encoding=DEFAULT_ENCODING, errors="replace") as f:
                content = f.read()
            logger.warning(
                "File '%s' contained characters that could not be decoded; "
                "replacement characters were inserted.",
                abs_path,
            )
        except OSError as e:
            raise ParseError(
                f"Could not read or decode file '{abs_path}' with any supported encoding.",
                cause=e,
            )

    file_type = "html" if ext in {".html", ".htm"} else "txt"
    return content, file_type