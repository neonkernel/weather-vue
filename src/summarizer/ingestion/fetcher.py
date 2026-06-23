"""HTTP fetching logic for article ingestion."""

from __future__ import annotations

import logging
from typing import Tuple

import requests
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    HTTPError,
    ReadTimeout,
    TooManyRedirects,
)

from src.summarizer.exceptions import FetchError

logger = logging.getLogger(__name__)

# Realistic browser User-Agent to avoid bot-blocking
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_DEFAULT_TIMEOUT = 15  # seconds
_MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
_ALLOWED_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
)


def fetch_url(url: str, timeout: int = _DEFAULT_TIMEOUT) -> Tuple[str, str]:
    """Fetch the HTML content of a URL.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        A tuple of (html_content, final_url) where final_url reflects any
        redirects that occurred.

    Raises:
        FetchError: On network errors, non-200 responses, or invalid content
            types.
    """
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    logger.info("Fetching URL: %s", url)

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
    except ReadTimeout as exc:
        raise FetchError(
            f"Request timed out after {timeout}s: {url}",
            source=url,
            cause=exc,
        ) from exc
    except TooManyRedirects as exc:
        raise FetchError(
            f"Too many redirects for URL: {url}",
            source=url,
            cause=exc,
        ) from exc
    except RequestsConnectionError as exc:
        raise FetchError(
            f"Connection error for URL: {url}",
            source=url,
            cause=exc,
        ) from exc
    except Exception as exc:
        raise FetchError(
            f"Unexpected error fetching URL: {url}",
            source=url,
            cause=exc,
        ) from exc

    final_url = response.url

    # Check HTTP status
    try:
        response.raise_for_status()
    except HTTPError as exc:
        raise FetchError(
            f"HTTP {response.status_code} error for URL: {final_url}",
            source=final_url,
            status_code=response.status_code,
            cause=exc,
        ) from exc

    # Validate content type
    content_type = response.headers.get("Content-Type", "").lower()
    if not any(ct in content_type for ct in _ALLOWED_CONTENT_TYPES):
        raise FetchError(
            f"Unsupported content type '{content_type}' for URL: {final_url}",
            source=final_url,
        )

    # Check content length before reading
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > _MAX_CONTENT_LENGTH:
        raise FetchError(
            f"Content too large ({content_length} bytes) for URL: {final_url}",
            source=final_url,
        )

    # Read content with size guard
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=8192, decode_unicode=False):
        total += len(chunk)
        if total > _MAX_CONTENT_LENGTH:
            raise FetchError(
                f"Content exceeded {_MAX_CONTENT_LENGTH} bytes for URL: {final_url}",
                source=final_url,
            )
        chunks.append(chunk)

    raw_bytes = b"".join(chunks)

    # Detect encoding from response or default to utf-8
    encoding = response.encoding or "utf-8"
    try:
        html = raw_bytes.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        html = raw_bytes.decode("utf-8", errors="replace")

    logger.info("Fetched %d bytes from %s", total, final_url)
    return html, final_url