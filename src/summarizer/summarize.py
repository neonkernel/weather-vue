"""Core summarization logic."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .models import Article, Summary
from .logger import get_logger

if TYPE_CHECKING:
    from .config import Config

logger = get_logger(__name__)


def _fetch_url(url: str) -> Article:
    """Fetch and parse an article from a URL."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ImportError(f"Missing dependency for URL fetching: {e}. Install requests and beautifulsoup4.") from e

    headers = {"User-Agent": "Mozilla/5.0 (compatible; ArticleSummarizer/1.0)"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    # Extract body text
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    word_count = len(text.split())

    return Article(url=url, title=title, text=text, word_count=word_count, source_type="url")


def _read_file(path: Path) -> Article:
    """Read an article from a local file (.txt or .html)."""
    content = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".html":
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else path.stem
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            source_type = "html"
        except ImportError:
            title = path.stem
            text = content
            source_type = "html"
    else:
        lines = content.splitlines()
        title = lines[0].strip() if lines else path.stem
        text = content
        source_type = "file"

    word_count = len(text.split())
    return Article(
        url=str(path),
        title=title,
        text=text,
        word_count=word_count,
        source_type=source_type,
    )


def _call_llm(article: Article, style: str, model: Optional[str], config) -> Summary:
    """Call the configured LLM to summarize the article."""
    from .llm import get_llm_client

    client = get_llm_client(config, model=model)
    result = client.summarize(article=article, style=style)
    return result


def summarize_source(
    source: str,
    style: str = "default",
    model: Optional[str] = None,
    config=None,
    dry_run: bool = False,
) -> tuple[Article, Summary]:
    """
    Fetch and summarize a source (URL or file path).
    Returns (Article, Summary).
    """
    from urllib.parse import urlparse

    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        article = _fetch_url(source)
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        article = _read_file(path)

    if dry_run:
        summary = Summary(
            text="[DRY RUN - LLM not called]",
            style=style,
            model=model or "dry-run",
            tokens_used=None,
            cost_estimate=None,
            dry_run=True,
        )
        return article, summary

    if config is None:
        from .config import load_config
        config = load_config()

    summary = _call_llm(article=article, style=style, model=model, config=config)
    return article, summary