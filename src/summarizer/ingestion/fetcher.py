"""HTTP fetching logic for article ingestion."""

import requests
from typing import Tuple

from src.summarizer.exceptions import FetchError

# Realistic browser User-Agent to avoid being blocked by many sites
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 15  # seconds
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10 MB


def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[str, str]:
    """
    Fetch the HTML content of a URL.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        A tuple of (html_content, final_url) where final_url accounts for redirects.

    Raises:
        FetchError: On network errors, timeouts, or non-200 HTTP responses.
    """
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
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
    except requests.exceptions.Timeout:
        raise FetchError(
            f"Request timed out after {timeout} seconds: {url}",
            url=url,
        )
    except requests.exceptions.TooManyRedirects:
        raise FetchError(
            f"Too many redirects while fetching: {url}",
            url=url,
        )
    except requests.exceptions.ConnectionError as exc:
        raise FetchError(
            f"Connection error while fetching '{url}': {exc}",
            url=url,
        )
    except requests.exceptions.RequestException as exc:
        raise FetchError(
            f"Unexpected request error while fetching '{url}': {exc}",
            url=url,
        )

    # Check HTTP status code
    if not response.ok:
        raise FetchError(
            f"HTTP {response.status_code} error fetching: {url}",
            url=url,
            status_code=response.status_code,
        )

    # Validate content type — we only handle HTML
    content_type = response.headers.get("Content-Type", "")
    if content_type and not any(
        ct in content_type for ct in ("text/html", "application/xhtml+xml", "text/plain")
    ):
        raise FetchError(
            f"Unexpected content type '{content_type}' for URL: {url}",
            url=url,
        )

    # Read content with size limit
    try:
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_CONTENT_SIZE:
                raise FetchError(
                    f"Response too large (>{MAX_CONTENT_SIZE // (1024*1024)} MB): {url}",
                    url=url,
                )
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(
            f"Error reading response content from '{url}': {exc}",
            url=url,
        )

    # Decode content — detect encoding from response or headers
    encoding = response.encoding or "utf-8"
    try:
        html = content.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        html = content.decode("utf-8", errors="replace")

    final_url = response.url  # May differ from original due to redirects
    return html, final_url