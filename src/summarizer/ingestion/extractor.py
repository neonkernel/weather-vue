"""HTML-to-text extraction using BeautifulSoup4 with a trafilatura fallback."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional, Tuple

from bs4 import BeautifulSoup, Tag

from src.summarizer.exceptions import ParseError

logger = logging.getLogger(__name__)

# Tags whose content should be removed entirely
_NOISE_TAGS = {
    "script", "style", "noscript", "iframe", "nav", "header", "footer",
    "aside", "form", "button", "input", "select", "textarea", "svg",
    "figure", "figcaption", "picture", "video", "audio", "canvas",
    "advertisement", "ads",
}

# CSS class/id substrings that indicate noise
_NOISE_PATTERNS = re.compile(
    r"(nav|navbar|navigation|menu|sidebar|footer|header|cookie|banner|"
    r"advertisement|ad-|ads|popup|modal|subscribe|newsletter|social|share|"
    r"comment|related|recommend|promo|widget|breadcrumb)",
    re.IGNORECASE,
)


def extract_text_from_html(html: str, url: str = "") -> Tuple[str, str]:
    """Extract the main article text and title from HTML content.

    Uses a fallback chain:
    1. trafilatura (high-quality extraction)
    2. Heuristic BeautifulSoup extractor (article/main/largest-div)

    Args:
        html: Raw HTML string.
        url: Source URL (used by trafilatura for context).

    Returns:
        A tuple of (title, text).

    Raises:
        ParseError: If no meaningful text could be extracted.
    """
    if not html or not html.strip():
        raise ParseError("Empty HTML content provided", source=url)

    title = _extract_title(html)

    # Try trafilatura first (best quality)
    text = _try_trafilatura(html, url)

    # Fall back to BeautifulSoup heuristics
    if not text or len(text.strip()) < 100:
        logger.debug("trafilatura failed or insufficient; using BS4 heuristics")
        text = _extract_with_bs4(html, url)

    if not text or len(text.strip()) < 50:
        raise ParseError(
            f"Could not extract meaningful text from HTML (source: {url or 'unknown'})",
            source=url,
        )

    text = normalize_text(text)
    return title, text


def _try_trafilatura(html: str, url: str = "") -> Optional[str]:
    """Attempt extraction with trafilatura."""
    try:
        import trafilatura

        result = trafilatura.extract(
            html,
            url=url or None,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=False,
            favor_recall=True,
        )
        return result
    except ImportError:
        logger.debug("trafilatura not installed; skipping")
        return None
    except Exception as exc:
        logger.debug("trafilatura extraction failed: %s", exc)
        return None


def _extract_with_bs4(html: str, url: str = "") -> str:
    """Heuristic extraction using BeautifulSoup4."""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        raise ParseError(f"Failed to parse HTML: {exc}", source=url, cause=exc) from exc

    # Remove noise elements
    _remove_noise(soup)

    # Try semantic containers in priority order
    for selector in ["article", "main", '[role="main"]', ".article-body",
                     ".post-content", ".entry-content", ".story-body", "#content"]:
        candidates = soup.select(selector)
        if candidates:
            text = _get_text(candidates[0])
            if len(text.split()) > 50:
                return text

    # Fall back to largest <div> by text density
    best = _find_largest_text_block(soup)
    if best:
        return _get_text(best)

    # Last resort: body text
    body = soup.find("body")
    if body:
        return _get_text(body)

    return soup.get_text(separator="\n")


def _remove_noise(soup: BeautifulSoup) -> None:
    """Remove known-noise tags and elements matching noise patterns."""
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue

        # Remove by tag name
        if tag.name in _NOISE_TAGS:
            tag.decompose()
            continue

        # Remove by class or id containing noise keywords
        classes = " ".join(tag.get("class", []))
        tag_id = tag.get("id", "")
        if _NOISE_PATTERNS.search(classes) or _NOISE_PATTERNS.search(tag_id):
            tag.decompose()


def _find_largest_text_block(soup: BeautifulSoup) -> Optional[Tag]:
    """Find the <div> with the highest text density (text-to-tag ratio)."""
    best_tag = None
    best_score = 0

    for div in soup.find_all("div"):
        text = div.get_text(separator=" ", strip=True)
        word_count = len(text.split())
        tag_count = len(div.find_all(True)) + 1  # avoid division by zero

        # Text density heuristic
        score = word_count / tag_count

        if score > best_score and word_count > 100:
            best_score = score
            best_tag = div

    return best_tag


def _get_text(tag: Tag) -> str:
    """Extract clean text from a tag with sensible whitespace."""
    return tag.get_text(separator="\n", strip=True)


def _extract_title(html: str) -> str:
    """Extract the page title from HTML."""
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Try Open Graph title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try Twitter title
        tw_title = soup.find("meta", attrs={"name": "twitter:title"})
        if tw_title and tw_title.get("content"):
            return tw_title["content"].strip()

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Fall back to <title> tag
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

    except Exception:
        pass

    return "Untitled"


def normalize_text(text: str) -> str:
    """Normalize extracted text by cleaning whitespace and special characters.

    - Removes zero-width and other invisible Unicode characters
    - Collapses multiple spaces to single space
    - Collapses 3+ consecutive blank lines to 2
    - Strips leading/trailing whitespace from each line
    - Normalizes Unicode to NFC form
    """
    if not text:
        return ""

    # Normalize Unicode form
    text = unicodedata.normalize("NFC", text)

    # Remove zero-width and invisible characters
    invisible_chars = re.compile(
        r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad\u00a0\u2028\u2029]"
    )
    text = invisible_chars.sub(" ", text)

    # Replace non-breaking spaces with regular spaces
    text = text.replace("\xa0", " ")

    # Strip each line and collapse multiple internal spaces
    lines = []
    for line in text.splitlines():
        line = re.sub(r" {2,}", " ", line).strip()
        lines.append(line)

    # Collapse 3+ consecutive blank lines into 2
    result_lines = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                result_lines.append(line)
        else:
            blank_count = 0
            result_lines.append(line)

    # Strip leading/trailing blank lines from the result
    text = "\n".join(result_lines).strip()

    return text