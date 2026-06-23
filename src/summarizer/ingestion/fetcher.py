"""HTTP fetching logic for article ingestion."""

import requests
from typing import Tuple
from src.summarizer.exceptions import FetchError

# Realistic browser User-Agent to avoid bot detection
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 15  # seconds
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

VALID_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/xml",
    "application/xml",
)


def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[str, str]:
    """
    Fetch HTML content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Tuple of (html_content, final_url) where final_url accounts for redirects

    Raises:
        FetchError: On network errors, HTTP errors, or invalid content type
    """
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
    except requests.exceptions.ConnectionError as e:
        raise FetchError(
            f"Could not connect to '{url}': {e}",
            url=url,
        ) from e
    except requests.exceptions.Timeout:
        raise FetchError(
            f"Request timed out after {timeout}s while fetching '{url}'",
            url=url,
        ) from None
    except requests.exceptions.TooManyRedirects:
        raise FetchError(
            f"Too many redirects while fetching '{url}'",
            url=url,
        ) from None
    except requests.exceptions.RequestException as e:
        raise FetchError(
            f"Failed to fetch '{url}': {e}",
            url=url,
        ) from e

    # Check HTTP status code
    if not response.ok:
        raise FetchError(
            f"HTTP {response.status_code} error fetching '{url}'",
            url=url,
            status_code=response.status_code,
        )

    # Validate content type
    content_type = response.headers.get("Content-Type", "").lower()
    if not any(ct in content_type for ct in VALID_CONTENT_TYPES):
        # Allow unknown content types with a warning — some servers misconfigure headers
        # but still serve valid HTML. Only reject clearly binary content.
        binary_types = ("application/pdf", "application/zip", "image/", "audio/", "video/")
        if any(bt in content_type for bt in binary_types):
            raise FetchError(
                f"Unsupported content type '{content_type}' for URL '{url}'",
                url=url,
            )

    # Check content length if provided
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_CONTENT_LENGTH:
        raise FetchError(
            f"Content too large ({content_length} bytes) for URL '{url}'",
            url=url,
        )

    # Read content with size limit
    chunks = []
    total_size = 0
    for chunk in response.iter_content(chunk_size=8192, decode_unicode=False):
        total_size += len(chunk)
        if total_size > MAX_CONTENT_LENGTH:
            raise FetchError(
                f"Content exceeded {MAX_CONTENT_LENGTH} bytes for URL '{url}'",
                url=url,
            )
        chunks.append(chunk)

    raw_bytes = b"".join(chunks)

    # Detect encoding
    encoding = response.encoding or "utf-8"
    try:
        html_content = raw_bytes.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        html_content = raw_bytes.decode("utf-8", errors="replace")

    final_url = response.url  # accounts for redirects

    return html_content, final_url