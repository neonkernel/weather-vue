"""HTML-to-text extraction using trafilatura and BeautifulSoup4."""

import re
import unicodedata
from typing import Optional

from src.summarizer.exceptions import ParseError
from src.summarizer.models import Article

# Try to import trafilatura (higher-quality extractor)
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

# Try to import newspaper3k as an alternative
try:
    from newspaper import Article as NewspaperArticle
    HAS_NEWSPAPER = True
except ImportError:
    HAS_NEWSPAPER = False

from bs4 import BeautifulSoup


def normalize_text(text: str) -> str:
    """
    Normalize extracted text:
    - Remove zero-width and invisible characters
    - Collapse multiple spaces/tabs into a single space
    - Strip excessive blank lines (max 2 consecutive)
    - Strip leading/trailing whitespace
    """
    if not text:
        return ""

    # Remove zero-width characters and other invisible Unicode
    zero_width_chars = [
        "\u200b",  # zero-width space
        "\u200c",  # zero-width non-joiner
        "\u200d",  # zero-width joiner
        "\u200e",  # left-to-right mark
        "\u200f",  # right-to-left mark
        "\ufeff",  # byte order mark / zero-width no-break space
        "\u00ad",  # soft hyphen
        "\u2060",  # word joiner
    ]
    for char in zero_width_chars:
        text = text.replace(char, "")

    # Normalize unicode (e.g., fancy quotes → standard)
    text = unicodedata.normalize("NFKC", text)

    # Replace non-breaking spaces and other whitespace variants with regular space
    text = text.replace("\xa0", " ").replace("\t", " ")

    # Collapse multiple spaces within lines
    lines = text.splitlines()
    lines = [re.sub(r" {2,}", " ", line).strip() for line in lines]

    # Remove excessive blank lines (allow max 1 consecutive blank line)
    cleaned_lines = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def extract_title_from_html(soup: BeautifulSoup) -> str:
    """Extract the best available title from HTML."""
    # Try Open Graph title first
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # Try Twitter card title
    twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
    if twitter_title and twitter_title.get("content"):
        return twitter_title["content"].strip()

    # Try <h1> inside article/main
    for container_tag in ("article", "main"):
        container = soup.find(container_tag)
        if container:
            h1 = container.find("h1")
            if h1:
                return h1.get_text(strip=True)

    # Try page <title>
    title_tag = soup.find("title")
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        # Remove common site name suffixes (e.g., "Article Title | Site Name")
        for separator in (" | ", " - ", " :: ", " — ", " – "):
            if separator in title_text:
                title_text = title_text.split(separator)[0].strip()
        return title_text

    # Fall back to first <h1> on the page
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return "Untitled Article"


def heuristic_extract(soup: BeautifulSoup) -> Optional[str]:
    """
    Heuristic HTML extraction using BeautifulSoup4.

    Strategy:
    1. Try <article> tag
    2. Try <main> tag
    3. Find the largest <div> by text density
    """
    # Remove noisy elements first
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer",
                     "aside", "iframe", "form", "button", "svg", "figure"]):
        tag.decompose()

    # Also remove elements with common ad/nav class/id patterns
    noise_patterns = re.compile(
        r"(nav|navbar|navigation|menu|sidebar|footer|header|cookie|banner|"
        r"advertisement|ad-|ads|social|share|comment|related|recommend|"
        r"popup|modal|newsletter|subscribe|promo)",
        re.IGNORECASE,
    )
    for tag in soup.find_all(True):
        tag_id = tag.get("id", "")
        tag_class = " ".join(tag.get("class", []))
        if noise_patterns.search(tag_id) or noise_patterns.search(tag_class):
            tag.decompose()

    # 1. Try <article>
    article_tag = soup.find("article")
    if article_tag:
        text = article_tag.get_text(separator="\n")
        if len(text.split()) > 50:
            return text

    # 2. Try <main>
    main_tag = soup.find("main")
    if main_tag:
        text = main_tag.get_text(separator="\n")
        if len(text.split()) > 50:
            return text

    # 3. Find the largest <div> by word count
    best_div = None
    best_word_count = 0

    for div in soup.find_all("div"):
        text = div.get_text(separator=" ")
        word_count = len(text.split())
        if word_count > best_word_count:
            best_word_count = word_count
            best_div = div

    if best_div and best_word_count > 50:
        return best_div.get_text(separator="\n")

    # 4. Fall back to full body text
    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n")
        if len(text.split()) > 20:
            return text

    return None


def extract_article(html: str, url: Optional[str] = None) -> Article:
    """
    Extract a clean Article from raw HTML content.

    Uses trafilatura as the primary extractor (highest quality),
    falls back to newspaper3k, then falls back to heuristic BeautifulSoup extraction.

    Args:
        html: Raw HTML string.
        url: Optional URL for metadata and trafilatura hints.

    Returns:
        An Article dataclass with title, text, url, and word_count.

    Raises:
        ParseError: If no usable text can be extracted.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title_from_html(soup)
    text = None

    # Strategy 1: trafilatura (best quality)
    if HAS_TRAFILATURA:
        try:
            extracted = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=False,
            )
            if extracted and len(extracted.split()) > 30:
                text = extracted

                # Try to get a better title from trafilatura metadata
                try:
                    metadata = trafilatura.extract_metadata(html, default_url=url)
                    if metadata and metadata.title:
                        title = metadata.title
                except Exception:
                    pass
        except Exception:
            pass  # Fall through to next strategy

    # Strategy 2: newspaper3k
    if text is None and HAS_NEWSPAPER:
        try:
            np_article = NewspaperArticle(url or "")
            np_article.set_html(html)
            np_article.parse()
            if np_article.text and len(np_article.text.split()) > 30:
                text = np_article.text
                if np_article.title:
                    title = np_article.title
        except Exception:
            pass  # Fall through to heuristic

    # Strategy 3: heuristic BeautifulSoup extraction
    if text is None:
        # Re-parse since we may have mutated soup in heuristic_extract
        fresh_soup = BeautifulSoup(html, "html.parser")
        text = heuristic_extract(fresh_soup)

    if not text or len(text.strip()) < 20:
        raise ParseError(
            "Failed to extract meaningful text from the article.",
            source=url or "unknown",
        )

    text = normalize_text(text)

    if not text or len(text.split()) < 10:
        raise ParseError(
            "Extracted text is too short to be a valid article.",
            source=url or "unknown",
        )

    return Article(
        title=title,
        text=text,
        url=url,
        word_count=len(text.split()),
    )