"""Core summarization logic."""
from __future__ import annotations

import time
import logging
from typing import Optional

from .config import Config
from .models import Article, Summary
from .exceptions import SummarizerError

logger = logging.getLogger(__name__)


def fetch_article(source: str, config: Optional[Config] = None) -> Article:
    """
    Fetch and parse an article from a URL or file path.

    Args:
        source: URL or local file path.
        config: Optional configuration object.

    Returns:
        Article object with content.
    """
    if config is None:
        config = Config()

    try:
        from .ingestion import load_article
        return load_article(source, config=config)
    except ImportError:
        logger.debug("Ingestion module not available, using fallback")

    # Fallback: basic file/URL loading
    if source.startswith("http://") or source.startswith("https://"):
        return _fetch_url(source)
    else:
        return _fetch_file(source)


def _fetch_url(url: str) -> Article:
    """Basic URL fetching fallback."""
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode("utf-8", errors="replace")
            # Strip basic HTML tags for content preview
            import re
            text = re.sub(r"<[^>]+>", " ", content)
            text = re.sub(r"\s+", " ", text).strip()
            return Article(
                url=url,
                title=_extract_title(content),
                content=text[:10000],
                source=url,
            )
    except Exception as exc:
        raise SummarizerError(f"Failed to fetch URL '{url}': {exc}") from exc


def _fetch_file(path: str) -> Article:
    """Basic local file loading fallback."""
    from pathlib import Path

    file_path = Path(path)
    if not file_path.exists():
        raise SummarizerError(f"File not found: {path}")

    content = file_path.read_text(encoding="utf-8", errors="replace")
    suffix = file_path.suffix.lower()

    if suffix == ".html":
        import re
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()
        title = _extract_title(content)
    else:
        text = content
        title = file_path.stem

    return Article(
        url=path,
        title=title,
        content=text[:10000],
        source=path,
    )


def _extract_title(html: str) -> str:
    """Extract title from HTML content."""
    import re
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return "Untitled"


def summarize_article(
    source: str,
    style: str = "default",
    config: Optional[Config] = None,
    use_cache: bool = True,
) -> Summary:
    """
    Fetch and summarize an article.

    Args:
        source: URL or local file path.
        style: Summary style.
        config: Optional configuration.
        use_cache: Whether to use caching.

    Returns:
        Summary object.
    """
    if config is None:
        config = Config()

    start = time.monotonic()

    # Fetch article
    article = fetch_article(source, config=config)

    # Try to use LLM module
    try:
        from .llm import generate_summary
        summary_text, tokens, cost = generate_summary(
            article=article,
            style=style,
            config=config,
            use_cache=use_cache,
        )
    except ImportError:
        logger.debug("LLM module not available, using placeholder")
        summary_text = f"[Summary of '{article.title}' – LLM not configured]"
        tokens = 0
        cost = 0.0

    duration = time.monotonic() - start

    return Summary(
        article=article,
        text=summary_text,
        style=style,
        model=getattr(config, "model", "unknown"),
        tokens_used=tokens,
        cost_estimate=cost,
        duration_seconds=duration,
    )