"""HTML-to-text extraction using BeautifulSoup4 and trafilatura."""

import re
import unicodedata
from typing import Optional, Tuple

from src.summarizer.exceptions import ParseError
from src.summarizer.models import Article, SourceType

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    from bs4 import BeautifulSoup, Tag
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# Tags that are purely structural/non-content
NOISE_TAGS = {
    "script", "style", "noscript", "iframe", "nav", "footer", "header",
    "aside", "form", "button", "input", "select", "textarea", "label",
    "svg", "canvas", "figure", "figcaption", "advertisement", "ads",
}

# Zero-width and invisible characters to strip
ZERO_WIDTH_CHARS = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad]")


def normalize_text(text: str) -> str:
    """
    Normalize extracted text:
    - Remove zero-width/invisible characters
    - Normalize Unicode to NFC
    - Collapse multiple spaces/tabs into a single space
    - Strip excessive blank lines (max 2 consecutive)
    - Strip leading/trailing whitespace
    """
    if not text:
        return ""

    # Remove zero-width characters
    text = ZERO_WIDTH_CHARS.sub("", text)

    # Normalize Unicode
    text = unicodedata.normalize("NFC", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple spaces/tabs within lines
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)

    # Collapse excessive blank lines (allow max 2 consecutive blank lines)
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

    return "\n".join(result_lines).strip()


def _extract_title_bs4(soup: "BeautifulSoup") -> str:
    """Extract the page title using BeautifulSoup."""
    # Try og:title first
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # Try <title> tag
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)

    # Try h1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return ""


def _remove_noise_tags(soup: "BeautifulSoup") -> None:
    """Remove noise/boilerplate tags from the soup in-place."""
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove hidden elements
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden")):
        tag.decompose()

    # Remove common ad/nav class patterns
    noise_patterns = re.compile(
        r"\b(ad|ads|advertisement|nav|navigation|sidebar|footer|header|"
        r"cookie|popup|modal|banner|promo|social|share|comment|related|"
        r"newsletter|subscribe)\b",
        re.IGNORECASE,
    )
    for tag in soup.find_all(True):
        classes = " ".join(tag.get("class", []))
        tag_id = tag.get("id", "")
        if noise_patterns.search(classes) or noise_patterns.search(tag_id):
            tag.decompose()


def _text_density(tag: "Tag") -> float:
    """Calculate text density of a tag (text length / total HTML length)."""
    html_len = len(str(tag))
    if html_len == 0:
        return 0.0
    text_len = len(tag.get_text())
    return text_len / html_len


def _heuristic_extract_bs4(soup: "BeautifulSoup") -> str:
    """
    Heuristic extraction using BeautifulSoup:
    1. Try <article> tag
    2. Try <main> tag
    3. Try largest <div> by text density
    4. Fall back to <body>
    """
    _remove_noise_tags(soup)

    # 1. Try <article>
    article_tag = soup.find("article")
    if article_tag:
        return article_tag.get_text(separator="\n")

    # 2. Try <main>
    main_tag = soup.find("main")
    if main_tag:
        return main_tag.get_text(separator="\n")

    # 3. Try the div with the highest text density and sufficient content
    best_div = None
    best_score = 0.0
    for div in soup.find_all("div"):
        text = div.get_text()
        word_count = len(text.split())
        if word_count < 50:  # Skip tiny divs
            continue
        density = _text_density(div)
        score = density * word_count
        if score > best_score:
            best_score = score
            best_div = div

    if best_div is not None:
        return best_div.get_text(separator="\n")

    # 4. Fall back to entire body
    body = soup.find("body")
    if body:
        return body.get_text(separator="\n")

    return soup.get_text(separator="\n")


def extract_article(html_content: str, url: Optional[str] = None) -> Article:
    """
    Extract a clean article from HTML content.

    Uses trafilatura as the primary extractor (best quality), with a
    BeautifulSoup4 heuristic fallback.

    Args:
        html_content: Raw HTML string.
        url: Optional URL hint for trafilatura's extraction heuristics.

    Returns:
        An Article dataclass with title, text, and word_count populated.

    Raises:
        ParseError: If extraction completely fails.
    """
    if not html_content or not html_content.strip():
        raise ParseError("Empty HTML content provided.", source=url or "")

    title = ""
    text = ""

    # --- Primary: trafilatura ---
    if HAS_TRAFILATURA:
        try:
            extracted = trafilatura.extract(
                html_content,
                url=url,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=False,
                favor_recall=True,
            )
            if extracted and len(extracted.strip()) > 100:
                text = extracted

            # Extract metadata separately
            metadata = trafilatura.extract_metadata(html_content, default_url=url)
            if metadata:
                title = metadata.title or ""
        except Exception:
            # trafilatura failed, will fall through to BeautifulSoup
            pass

    # --- Fallback: BeautifulSoup heuristics ---
    if not text and HAS_BS4:
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            if not title:
                title = _extract_title_bs4(soup)
            text = _heuristic_extract_bs4(soup)
        except Exception as exc:
            raise ParseError(
                f"BeautifulSoup extraction failed: {exc}",
                source=url or "",
            )

    if not text:
        # Last resort: try to get title at least from BS4
        if HAS_BS4:
            try:
                soup = BeautifulSoup(html_content, "html.parser")
                if not title:
                    title = _extract_title_bs4(soup)
            except Exception:
                pass
        raise ParseError(
            "Could not extract article text from HTML content.",
            source=url or "",
        )

    # Normalize extracted text
    text = normalize_text(text)

    if not text:
        raise ParseError(
            "Extracted text is empty after normalization.",
            source=url or "",
        )

    word_count = len(text.split())

    return Article(
        title=normalize_text(title),
        text=text,
        url=url,
        word_count=word_count,
        source_type=SourceType.URL if url else SourceType.FILE,
    )