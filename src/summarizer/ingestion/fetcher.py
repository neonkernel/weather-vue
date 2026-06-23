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
        FetchError: On network errors, timeouts, HTTP errors, or unsupported content types.
    """
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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
            f"Request timed out after {timeout} seconds.",
            url=url,
        )
    except requests.exceptions.ConnectionError as e:
        raise FetchError(
            f"Connection error while fetching URL: {e}",
            url=url,
        )
    except requests.exceptions.TooManyRedirects:
        raise FetchError(
            "Too many redirects while following URL.",
            url=url,
        )
    except requests.exceptions.RequestException as e:
        raise FetchError(
            f"Unexpected request error: {e}",
            url=url,
        )

    # Check HTTP status
    if not response.ok:
        raise FetchError(
            f"HTTP error {response.status_code}: {response.reason}",
            url=url,
            status_code=response.status_code,
        )

    # Validate content type — we only handle HTML/text
    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and not any(
        ct in content_type for ct in ("text/html", "application/xhtml", "text/plain")
    ):
        raise FetchError(
            f"Unsupported content type: {content_type}. Expected HTML.",
            url=url,
        )

    # Read content with size cap
    try:
        content = response.content[:MAX_CONTENT_SIZE]
    except Exception as e:
        raise FetchError(f"Failed to read response content: {e}", url=url)

    # Detect encoding
    encoding = response.encoding or "utf-8"
    if encoding.lower() in ("iso-8859-1", "latin-1"):
        # requests often defaults to latin-1; try utf-8 first
        try:
            html_text = content.decode("utf-8")
        except UnicodeDecodeError:
            html_text = content.decode(encoding, errors="replace")
    else:
        try:
            html_text = content.decode(encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            html_text = content.decode("utf-8", errors="replace")

    final_url = response.url  # May differ from input due to redirects
    return html_text, final_url