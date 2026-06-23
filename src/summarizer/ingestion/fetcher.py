"""HTTP fetching logic for article ingestion."""

import logging
from typing import Tuple

import requests
from requests.exceptions import (
    ConnectionError,
    ReadTimeout,
    TooManyRedirects,
    RequestException,
)

from src.summarizer.exceptions import FetchError

logger = logging.getLogger(__name__)

# Realistic browser User-Agent to avoid being blocked by sites
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 15  # seconds
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

ALLOWED_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
)


def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[str, str]:
    """
    Fetch the content of a URL and return the HTML text plus the final URL
    (after any redirects).

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        A tuple of (html_content: str, final_url: str).

    Raises:
        FetchError: On network errors, HTTP errors, timeouts, or unsupported content types.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
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
            stream=True,  # Use streaming to check content-length before downloading
        )
    except ReadTimeout as e:
        raise FetchError(
            f"Request timed out after {timeout}s.",
            url=url,
            cause=e,
        )
    except TooManyRedirects as e:
        raise FetchError(
            "Too many redirects while fetching URL.",
            url=url,
            cause=e,
        )
    except ConnectionError as e:
        raise FetchError(
            "Could not connect to the server. Check the URL and your internet connection.",
            url=url,
            cause=e,
        )
    except RequestException as e:
        raise FetchError(
            f"Unexpected network error: {e}",
            url=url,
            cause=e,
        )

    final_url = response.url

    # Check HTTP status
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        raise FetchError(
            f"HTTP {response.status_code} error fetching URL.",
            url=final_url,
            cause=e,
        )

    # Validate content type
    content_type = response.headers.get("Content-Type", "")
    if not any(allowed in content_type for allowed in ALLOWED_CONTENT_TYPES):
        raise FetchError(
            f"Unsupported content type: '{content_type}'. Expected HTML or plain text.",
            url=final_url,
        )

    # Check content length before reading
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_CONTENT_LENGTH:
        raise FetchError(
            f"Content too large: {int(content_length) / (1024*1024):.1f} MB (max {MAX_CONTENT_LENGTH // (1024*1024)} MB).",
            url=final_url,
        )

    # Read content with a size guard
    chunks = []
    total_size = 0
    try:
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=False):
            total_size += len(chunk)
            if total_size > MAX_CONTENT_LENGTH:
                raise FetchError(
                    f"Content exceeds maximum allowed size of {MAX_CONTENT_LENGTH // (1024*1024)} MB.",
                    url=final_url,
                )
            chunks.append(chunk)
    except FetchError:
        raise
    except RequestException as e:
        raise FetchError(
            f"Error reading response body: {e}",
            url=final_url,
            cause=e,
        )

    raw_bytes = b"".join(chunks)

    # Detect encoding from response or default to UTF-8
    encoding = response.encoding or response.apparent_encoding or "utf-8"
    try:
        html_content = raw_bytes.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        html_content = raw_bytes.decode("utf-8", errors="replace")

    logger.info(
        "Fetched %d bytes from %s (encoding: %s)",
        total_size,
        final_url,
        encoding,
    )

    return html_content, final_url