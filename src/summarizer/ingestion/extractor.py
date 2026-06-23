"""HTML-to-text extraction using BeautifulSoup4 and trafilatura."""

import logging
import re
import unicodedata
from typing import Optional

from src.summarizer.exceptions import ParseError
from src.summarizer.models import Article, SourceType

logger = logging.getLogger(__name__)

# Tags whose content should be removed entirely
NOISE_TAGS = {
    "script", "style", "noscript", "iframe", "nav", "footer",
    "header", "aside", "form", "button", "select", "option",
    "figure", "figcaption", "advertisement", "ads",
}

# Meta tag names that may contain the article title
TITLE_META_NAMES = [
    ("property", "og:title"),
    ("name", "twitter:title"),
    ("name", "title"),
]


def normalize_text(text: str) -> str:
    """
    Normalize extracted text:
    - Remove zero-width and other invisible Unicode characters
    - Collapse multiple spaces/tabs into a single space
    - Strip excessive blank lines (max 2 consecutive newlines)
    - Strip leading/trailing whitespace
    """
    if not text:
        return ""

    # Remove zero-width characters and other invisible Unicode
    text = "".join(
        ch for ch in text
        if not unicodedata.category(ch).startswith("C") or ch in ("\n", "\t", "\r")
    )

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces on each line
    lines = [re.sub(r" {2,}", " ", line).strip() for line in text.split("\n")]

    # Collapse more than 2 consecutive blank lines
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


def _extract_title_from_html(soup) -> str:
    """Extract the best available title from HTML soup."""
    # Try Open Graph / Twitter meta tags first
    for attr, value in TITLE_META_NAMES:
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            return tag["content"].strip()

    # Try <title> tag
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        return title_tag.get_text(strip=True)

    # Try h1
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    return ""


def _remove_noise(soup):
    """Remove noise tags from BeautifulSoup tree in-place."""
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove elements with common ad/nav class or id patterns
    noise_patterns = re.compile(
        r"(nav|navigation|sidebar|footer|header|cookie|banner|ad[-_]|"
        r"advertisement|social|share|comment|related|recommend|popup|modal|"
        r"newsletter|subscribe)",
        re.IGNORECASE,
    )
    for tag in soup.find_all(True):
        cls = " ".join(tag.get("class", []))
        tag_id = tag.get("id", "")
        if noise_patterns.search(cls) or noise_patterns.search(tag_id):
            tag.decompose()

    return soup


def _heuristic_extract(soup) -> str:
    """
    Heuristic extraction chain:
    1. <article> tag
    2. <main> tag
    3. Largest <div> by text density
    """
    # 1. Try <article>
    article_tag = soup.find("article")
    if article_tag:
        text = article_tag.get_text(separator="\n")
        if len(text.split()) > 50:
            logger.debug("Extracted text from <article> tag.")
            return text

    # 2. Try <main>
    main_tag = soup.find("main")
    if main_tag:
        text = main_tag.get_text(separator="\n")
        if len(text.split()) > 50:
            logger.debug("Extracted text from <main> tag.")
            return text

    # 3. Find the <div> with the highest text density
    best_div = None
    best_score = 0

    for div in soup.find_all("div"):
        text = div.get_text(separator=" ")
        word_count = len(text.split())
        # Penalize divs with lots of links (nav-heavy blocks)
        link_count = len(div.find_all("a"))
        score = word_count - (link_count * 3)
        if score > best_score:
            best_score = score
            best_div = div

    if best_div and best_score > 30:
        logger.debug("Extracted text from best <div> by text density (score=%d).", best_score)
        return best_div.get_text(separator="\n")

    # 4. Fallback: entire body
    body = soup.find("body")
    if body:
        logger.debug("Falling back to full <body> text extraction.")
        return body.get_text(separator="\n")

    return soup.get_text(separator="\n")


def _try_trafilatura(html: str, url: Optional[str] = None) -> Optional[str]:
    """Attempt extraction with trafilatura; return None if unavailable or failed."""
    try:
        import trafilatura

        result = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )
        return result
    except ImportError:
        logger.debug("trafilatura not installed; skipping.")
        return None
    except Exception as e:
        logger.debug("trafilatura extraction failed: %s", e)
        return None


def _try_newspaper(html: str, url: Optional[str] = None) -> Optional[str]:
    """Attempt extraction with newspaper3k; return None if unavailable or failed."""
    try:
        from newspaper import Article as NewspaperArticle

        article = NewspaperArticle(url or "http://localhost/")
        article.set_html(html)
        article.parse()
        text = article.text
        return text if text and len(text.split()) > 30 else None
    except ImportError:
        logger.debug("newspaper3k not installed; skipping.")
        return None
    except Exception as e:
        logger.debug("newspaper3k extraction failed: %s", e)
        return None


def extract_article(html: str, url: Optional[str] = None) -> Article:
    """
    Extract article content from raw HTML.

    Extraction chain (highest to lowest quality):
    1. trafilatura
    2. newspaper3k
    3. BeautifulSoup heuristic extractor

    Args:
        html: Raw HTML string.
        url: Original URL (used as hint by extraction libraries).

    Returns:
        An Article dataclass.

    Raises:
        ParseError: If no readable text can be extracted.
    """
    if not html or not html.strip():
        raise ParseError("Empty HTML content provided.")

    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ParseError("BeautifulSoup4 is not installed. Run: pip install beautifulsoup4", cause=e)

    # Parse HTML for title and heuristic extraction
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title_from_html(soup)

    # --- Extraction chain ---
    text = None

    # 1. Try trafilatura (best quality for news/blog)
    text = _try_trafilatura(html, url=url)
    if text and len(text.split()) > 30:
        logger.info("Used trafilatura for extraction.")
    else:
        # 2. Try newspaper3k
        text = _try_newspaper(html, url=url)
        if text and len(text.split()) > 30:
            logger.info("Used newspaper3k for extraction.")
        else:
            # 3. BeautifulSoup heuristic
            logger.info("Using BeautifulSoup heuristic extraction.")
            clean_soup = BeautifulSoup(html, "html.parser")
            _remove_noise(clean_soup)
            text = _heuristic_extract(clean_soup)

    if not text:
        raise ParseError("Could not extract any readable text from the HTML.")

    # Normalize the extracted text
    text = normalize_text(text)

    if not text or len(text.split()) < 10:
        raise ParseError(
            "Extracted text is too short to be a valid article "
            f"({len(text.split())} words). The page may require JavaScript or "
            "the content may be behind a paywall."
        )

    return Article.from_text(text=text, title=title, url=url, source_type=SourceType.URL)