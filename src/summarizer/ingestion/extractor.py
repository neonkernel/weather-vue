"""HTML-to-text extraction using BeautifulSoup4 and trafilatura."""

import re
import unicodedata
from typing import Optional
from src.summarizer.models import Article
from src.summarizer.exceptions import ParseError

try:
    from bs4 import BeautifulSoup, Tag
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

# Tags that typically contain boilerplate/noise
NOISE_TAGS = {
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "advertisement", "figure", "figcaption", "iframe",
    "form", "button", "input", "select", "textarea", "label",
    "menu", "menuitem", "dialog", "template", "svg", "canvas",
}

# CSS class/id patterns that indicate boilerplate
NOISE_PATTERNS = re.compile(
    r"(nav|navbar|navigation|menu|sidebar|footer|header|advertisement|"
    r"banner|cookie|popup|modal|overlay|social|share|comment|related|"
    r"recommended|trending|newsletter|subscribe|promo|ad-|ads-|widget)",
    re.IGNORECASE,
)


def extract_article(html: str, url: str = "") -> Article:
    """
    Extract clean article text from HTML content.

    Uses a fallback chain:
    1. trafilatura (best quality for news/blogs)
    2. BeautifulSoup heuristic extraction (<article>, <main>, largest <div>)
    3. Full body text as last resort

    Args:
        html: Raw HTML string
        url: Source URL (used for trafilatura metadata)

    Returns:
        Article dataclass with extracted title and text

    Raises:
        ParseError: If no text can be extracted
    """
    if not html or not html.strip():
        raise ParseError("Empty HTML content provided", source=url)

    title = ""
    text = ""

    # Strategy 1: trafilatura (highest quality)
    if TRAFILATURA_AVAILABLE:
        try:
            extracted = trafilatura.extract(
                html,
                url=url or None,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=False,
            )
            if extracted and len(extracted.strip()) > 100:
                text = normalize_text(extracted)
                # Try to get metadata for title
                meta = trafilatura.extract_metadata(html, default_url=url or None)
                if meta and meta.title:
                    title = meta.title.strip()

        except Exception:
            pass  # Fall through to next strategy

    # Strategy 2: BeautifulSoup heuristic extraction
    if not text and BS4_AVAILABLE:
        try:
            title_bs, text_bs = _extract_with_bs4(html)
            if text_bs and len(text_bs.strip()) > 50:
                text = normalize_text(text_bs)
                if not title and title_bs:
                    title = title_bs
        except Exception as e:
            if not text:
                raise ParseError(f"BeautifulSoup extraction failed: {e}", source=url) from e

    if not text:
        raise ParseError(
            "Could not extract any meaningful text from the HTML content",
            source=url,
        )

    if not title:
        title = _infer_title(text)

    return Article(
        title=title,
        text=text,
        url=url or None,
        word_count=len(text.split()),
    )


def _extract_with_bs4(html: str):
    """
    Extract title and body text using BeautifulSoup heuristics.

    Returns:
        Tuple of (title, text)
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Also check og:title or h1 for cleaner titles
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    # Remove noise elements
    _remove_noise_elements(soup)

    # Try semantic content containers in order
    content_tag = None

    article_tag = soup.find("article")
    if article_tag:
        content_tag = article_tag
    else:
        main_tag = soup.find("main")
        if main_tag:
            content_tag = main_tag

    # Fallback: find the <div> with highest text density
    if not content_tag:
        content_tag = _find_content_div(soup)

    # Last resort: use body
    if not content_tag:
        content_tag = soup.find("body") or soup

    text = _extract_text_from_tag(content_tag)
    return title, text


def _remove_noise_elements(soup):
    """Remove tags that typically contain boilerplate content."""
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    # Remove elements whose class or id match noise patterns
    for tag in soup.find_all(True):
        classes = " ".join(tag.get("class", []))
        tag_id = tag.get("id", "")
        if NOISE_PATTERNS.search(classes) or NOISE_PATTERNS.search(tag_id):
            tag.decompose()


def _find_content_div(soup) -> Optional["Tag"]:
    """
    Find the <div> block most likely to contain the main article content
    by using text density (text length / total tag count).
    """
    best_tag = None
    best_score = 0

    candidates = soup.find_all("div")
    for div in candidates:
        text = div.get_text(separator=" ", strip=True)
        text_length = len(text)
        if text_length < 200:
            continue

        # Count child tags as a measure of "noise"
        tag_count = max(len(div.find_all(True)), 1)
        density = text_length / tag_count

        if density > best_score:
            best_score = density
            best_tag = div

    return best_tag


def _extract_text_from_tag(tag) -> str:
    """Extract readable text from a BeautifulSoup tag."""
    # Use newlines between block elements
    lines = []
    for element in tag.descendants:
        if hasattr(element, "name"):
            if element.name in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br"):
                text = element.get_text(separator=" ", strip=True)
                if text:
                    lines.append(text)
        # Also capture direct NavigableString children
    if not lines:
        lines = [tag.get_text(separator="\n", strip=True)]
    return "\n".join(lines)


def _infer_title(text: str, max_length: int = 80) -> str:
    """Infer a title from the first line of extracted text."""
    first_line = text.strip().split("\n")[0].strip()
    if len(first_line) <= max_length:
        return first_line
    return first_line[:max_length].rsplit(" ", 1)[0] + "…"


def normalize_text(text: str) -> str:
    """
    Normalize extracted text:
    - Collapse excessive whitespace
    - Remove zero-width and invisible Unicode characters
    - Strip excessive blank lines
    - Normalize Unicode to NFC form
    """
    if not text:
        return ""

    # Normalize Unicode to NFC
    text = unicodedata.normalize("NFC", text)

    # Remove zero-width characters and other invisible Unicode
    zero_width_chars = [
        "\u200b",  # Zero-width space
        "\u200c",  # Zero-width non-joiner
        "\u200d",  # Zero-width joiner
        "\u200e",  # Left-to-right mark
        "\u200f",  # Right-to-left mark
        "\ufeff",  # BOM / Zero-width no-break space
        "\u00ad",  # Soft hyphen
        "\u2060",  # Word joiner
    ]
    for char in zero_width_chars:
        text = text.replace(char, "")

    # Replace non-breaking spaces with regular spaces
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2009", " ")  # thin space
    text = text.replace("\u202f", " ")  # narrow no-break space

    # Collapse multiple spaces/tabs on each line
    lines = text.split("\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]

    # Remove lines that are pure whitespace or very short noise lines
    # (keep lines with at least 2 characters to preserve short words)
    lines = [line for line in lines if len(line) >= 2]

    # Collapse more than 2 consecutive blank lines to 2
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

    text = "\n".join(result_lines).strip()
    return text