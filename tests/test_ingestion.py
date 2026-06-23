"""Unit tests for article ingestion: fetcher, extractor, and file_reader."""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.summarizer.ingestion.fetcher import fetch_url
from src.summarizer.ingestion.extractor import (
    extract_article,
    normalize_text,
    heuristic_extract,
)
from src.summarizer.ingestion.file_reader import read_file
from src.summarizer.ingestion import fetch_article
from src.summarizer.models import Article, SourceType
from src.summarizer.exceptions import FetchError, ParseError

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_HTML_PATH = FIXTURES_DIR / "sample_article.html"
SAMPLE_TXT_PATH = FIXTURES_DIR / "sample_article.txt"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_html() -> str:
    """Return the sample article HTML as a string."""
    return SAMPLE_HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture
def sample_txt() -> str:
    """Return the sample article plain text as a string."""
    return SAMPLE_TXT_PATH.read_text(encoding="utf-8")


@pytest.fixture
def minimal_html() -> str:
    """Return a minimal valid HTML article."""
    return """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
<article>
<h1>Test Article Heading</h1>
<p>This is the first paragraph of the test article with enough words to pass validation.</p>
<p>This is the second paragraph providing more content for the article body text.</p>
<p>And a third paragraph to make sure there is sufficient word count for extraction.</p>
</article>
</body>
</html>"""


@pytest.fixture
def noisy_html() -> str:
    """Return HTML with lots of boilerplate noise."""
    return """<!DOCTYPE html>
<html>
<head><title>Noisy Page | Site Name</title></head>
<body>
<nav id="navbar"><a href="/">Home</a><a href="/about">About</a></nav>
<header><h2>Site Header</h2></header>
<div class="advertisement"><p>Buy stuff now!</p></div>
<aside class="sidebar"><p>Related: <a href="/other">Other article</a></p></aside>
<article>
  <h1>Clean Article Title</h1>
  <p>This is the actual article content that should be extracted cleanly without
  the surrounding navigation, advertisements, or sidebar content appearing in
  the final output after extraction and normalization processing.</p>
  <p>Here is a second paragraph of the article with more meaningful content
  that further validates the extraction process works correctly for real-world
  HTML pages found on the web today.</p>
</article>
<footer><p>Copyright 2026</p></footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# normalize_text tests
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_removes_zero_width_characters(self):
        text = "Hello\u200bWorld\u200c!"
        result = normalize_text(text)
        assert "\u200b" not in result
        assert "\u200c" not in result
        assert "HelloWorld!" in result

    def test_collapses_multiple_spaces(self):
        text = "Hello    World   foo"
        result = normalize_text(text)
        assert "Hello World foo" in result

    def test_strips_excessive_blank_lines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = normalize_text(text)
        blank_count = sum(1 for line in result.splitlines() if line == "")
        assert blank_count <= 1

    def test_normalizes_non_breaking_spaces(self):
        text = "Hello\xa0World"
        result = normalize_text(text)
        assert "\xa0" not in result
        assert "Hello World" in result

    def test_strips_leading_trailing_whitespace(self):
        text = "   \n  Hello World  \n   "
        result = normalize_text(text)
        assert result == result.strip()

    def test_empty_string_returns_empty(self):
        assert normalize_text("") == ""

    def test_none_equivalent_empty(self):
        # Empty string is falsy like None
        result = normalize_text("")
        assert result == ""

    def test_normalizes_tabs(self):
        text = "Hello\tWorld\tFoo"
        result = normalize_text(text)
        assert "\t" not in result


# ---------------------------------------------------------------------------
# Fetcher tests (mocked requests)
# ---------------------------------------------------------------------------

class TestFetchUrl:
    def _make_mock_response(
        self,
        status_code=200,
        content=b"<html><body>Hello</body></html>",
        content_type="text/html; charset=utf-8",
        encoding="utf-8",
        url="https://example.com/article",
    ):
        mock_resp = MagicMock()
        mock_resp.ok = status_code < 400
        mock_resp.status_code = status_code
        mock_resp.reason = "OK" if status_code == 200 else "Error"
        mock_resp.content = content
        mock_resp.encoding = encoding
        mock_resp.url = url
        mock_resp.headers = {"Content-Type": content_type}
        return mock_resp

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_successful_fetch(self, mock_get, minimal_html):
        mock_get.return_value = self._make_mock_response(
            content=minimal_html.encode("utf-8")
        )
        html, url = fetch_url("https://example.com/article")
        assert "<article>" in html
        assert url == "https://example.com/article"

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_returns_final_url_after_redirect(self, mock_get, minimal_html):
        mock_get.return_value = self._make_mock_response(
            content=minimal_html.encode("utf-8"),
            url="https://example.com/redirected-article",
        )
        _, final_url = fetch_url("https://example.com/article")
        assert final_url == "https://example.com/redirected-article"

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_404(self, mock_get):
        mock_get.return_value = self._make_mock_response(status_code=404)
        mock_get.return_value.ok = False
        mock_get.return_value.reason = "Not Found"
        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/missing")
        assert exc_info.value.status_code == 404

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_500(self, mock_get):
        mock_get.return_value = self._make_mock_response(status_code=500)
        mock_get.return_value.ok = False
        mock_get.return_value.reason = "Internal Server Error"
        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/error")
        assert exc_info.value.status_code == 500

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_timeout(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.Timeout()
        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/slow")
        assert "timed out" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_connection_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError("DNS failure")
        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://nonexistent.example.invalid/")
        assert "connection error" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_too_many_redirects(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.TooManyRedirects()
        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/redirect-loop")
        assert "redirect" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_unsupported_content_type(self, mock_get):
        mock_get.return_value = self._make_mock_response(
            content_type="application/pdf"
        )
        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/file.pdf")
        assert "content type" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_sends_user_agent_header(self, mock_get, minimal_html):
        mock_get.return_value = self._make_mock_response(
            content=minimal_html.encode("utf-8")
        )
        fetch_url("https://example.com/article")
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_handles_latin1_encoding(self, mock_get):
        content = "<html><body><article><p>{}</p></article></body></html>".format(
            "A" * 200
        )
        mock_get.return_value = self._make_mock_response(
            content=content.encode("latin-1"),
            encoding="iso-8859-1",
        )
        html, _ = fetch_url("https://example.com/article")
        assert html is not None
        assert len(html) > 0


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------

class TestExtractArticle:
    def test_extracts_from_sample_html_fixture(self, sample_html):
        article = extract_article(sample_html, url="https://example.com/energy")
        assert article.title != ""
        assert len(article.text.split()) > 100
        assert article.word_count > 100
        assert article.url == "https://example.com/energy"

    def test_extracts_title_from_og_meta(self, sample_html):
        article = extract_article(sample_html)
        # OG title is "The Future of Renewable Energy"
        assert "Renewable Energy" in article.title or "renewable" in article.title.lower()

    def test_extracts_meaningful_text(self, minimal_html):
        article = extract_article(minimal_html)
        assert "paragraph" in article.text.lower()
        assert len(article.text.split()) >= 10

    def test_strips_navigation_from_noisy_html(self, noisy_html):
        article = extract_article(noisy_html)
        # Navigation text should not appear in extracted content
        # (heuristic: nav items like "Home" and "About" as standalone words should be gone)
        assert "Buy stuff now" not in article.text
        assert "article content" in article.text.lower()

    def test_word_count_matches_text(self, minimal_html):
        article = extract_article(minimal_html)
        assert article.word_count == len(article.text.split())

    def test_raises_parse_error_on_empty_html(self):
        with pytest.raises(ParseError):
            extract_article("")

    def test_raises_parse_error_on_no_content_html(self):
        html = "<html><head><title>Empty</title></head><body></body></html>"
        with pytest.raises(ParseError):
            extract_article(html)

    def test_raises_parse_error_on_script_only_page(self):
        html = "<html><body><script>var x = 1;</script></body></html>"
        with pytest.raises(ParseError):
            extract_article(html)

    def test_url_stored_in_article(self, minimal_html):
        url = "https://example.com/test"
        article = extract_article(minimal_html, url=url)
        assert article.url == url

    def test_url_none_when_not_provided(self, minimal_html):
        article = extract_article(minimal_html)
        assert article.url is None

    def test_text_is_normalized(self, sample_html):
        article = extract_article(sample_html)
        # Should not have excessive blank lines
        lines = article.text.splitlines()
        consecutive_blanks = 0
        for line in lines:
            if line.strip() == "":
                consecutive_blanks += 1
                assert consecutive_blanks <= 2, "Too many consecutive blank lines"
            else:
                consecutive_blanks = 0


class TestHeuristicExtract:
    def test_prefers_article_tag(self):
        from bs4 import BeautifulSoup
        html = """<html><body>
        <div>Noise noise noise noise noise noise noise noise noise noise noise</div>
        <article><p>This is the real article content with sufficient words to pass validation checks.</p>
        <p>Second paragraph with more meaningful content for the article body.</p></article>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        text = heuristic_extract(soup)
        assert text is not None
        assert "real article" in text.lower()

    def test_falls_back_to_main_tag(self):
        from bs4 import BeautifulSoup
        html = """<html><body>
        <main><p>Main content area with the article text and enough words here.</p>
        <p>Another paragraph in main for additional content.</p></main>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        text = heuristic_extract(soup)
        assert text is not None
        assert "main content" in text.lower()

    def test_returns_none_for_empty_body(self):
        from bs4 import BeautifulSoup
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = heuristic_extract(soup)
        # Either None or very short text
        if text is not None:
            assert len(text.split()) < 5


# ---------------------------------------------------------------------------
# File reader tests
# ---------------------------------------------------------------------------

class TestReadFile:
    def test_reads_txt_file(self):
        article = read_file(str(SAMPLE_TXT_PATH))
        assert article.source_type == SourceType.FILE
        assert len(article.text.split()) > 50
        assert article.word_count > 50

    def test_reads_html_file(self):
        article = read_file(str(SAMPLE_HTML_PATH))
        assert article.source_type == SourceType.FILE
        assert len(article.text.split()) > 50

    def test_txt_article_url_is_filepath(self):
        article = read_file(str(SAMPLE_TXT_PATH))
        assert article.url == str(SAMPLE_TXT_PATH)

    def test_html_article_url_is_filepath(self):
        article = read_file(str(SAMPLE_HTML_PATH))
        assert article.url == str(SAMPLE_HTML_PATH)

    def test_txt_title_from_filename(self):
        article = read_file(str(SAMPLE_TXT_PATH))
        # File is sample_article.txt, title should be derived from stem
        assert article.title != ""
        assert len(article.title) > 0

    def test_raises_fetch_error_for_missing_file(self):
        with pytest.raises(FetchError) as exc_info:
            read_file("/nonexistent/path/to/file.txt")
        assert "not found" in str(exc_info.value).lower()

    def test_raises_parse_error_for_unsupported_extension(self, tmp_path):
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_text("fake pdf content")
        with pytest.raises(ParseError) as exc_info:
            read_file(str(pdf_file))
        assert "unsupported" in str(exc_info.value).lower()

    def test_raises_parse_error_for_empty_txt_file(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        with pytest.raises(ParseError):
            read_file(str(empty_file))

    def test_raises_parse_error_for_whitespace_only_file(self, tmp_path):
        blank_file = tmp_path / "blank.txt"
        blank_file.write_text("   \n\n\t\n   ")
        with pytest.raises(ParseError):
            read_file(str(blank_file))

    def test_reads_html_extension_htm(self, tmp_path):
        htm_content = """<html><head><title>HTM Test</title></head>
<body><article>
<h1>HTM Test Article</h1>
<p>This is a test article in an HTM file with enough content to pass validation checks.</p>
<p>Here is a second paragraph with additional content for the HTM test article extraction.</p>
</article></body></html>"""
        htm_file = tmp_path / "test.htm"
        htm_file.write_text(htm_content, encoding="utf-8")
        article = read_file(str(htm_file))
        assert article.source_type == SourceType.FILE
        assert len(article.text.split()) > 10

    def test_word_count_matches_text_for_txt(self):
        article = read_file(str(SAMPLE_TXT_PATH))
        assert article.word_count == len(article.text.split())


# ---------------------------------------------------------------------------
# fetch_article integration tests
# ---------------------------------------------------------------------------

class TestFetchArticle:
    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_fetch_article_from_url(self, mock_get, sample_html):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = sample_html.encode("utf-8")
        mock_resp.encoding = "utf-8"
        mock_resp.url = "https://example.com/energy-article"
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_get.return_value = mock_resp

        article = fetch_article("https://example.com/energy-article")
        assert isinstance(article, Article)
        assert article.source_type == SourceType.URL
        assert len(article.text.split()) > 50

    def test_fetch_article_from_txt_file(self):
        article = fetch_article(str(SAMPLE_TXT_PATH))
        assert isinstance(article, Article)
        assert article.source_type == SourceType.FILE
        assert len(article.text.split()) > 50

    def test_fetch_article_from_html_file(self):
        article = fetch_article(str(SAMPLE_HTML_PATH))
        assert isinstance(article, Article)
        assert article.source_type == SourceType.FILE
        assert len(article.text.split()) > 50

    def test_fetch_article_raises_fetch_error_for_missing_file(self):
        with pytest.raises(FetchError):
            fetch_article("/no/such/file.txt")

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_fetch_article_raises_fetch_error_on_http_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 403
        mock_resp.reason = "Forbidden"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_get.return_value = mock_resp

        with pytest.raises(FetchError):
            fetch_article("https://example.com/forbidden")

    def test_fetch_article_article_has_required_fields(self):
        article = fetch_article(str(SAMPLE_TXT_PATH))
        assert hasattr(article, "title")
        assert hasattr(article, "text")
        assert hasattr(article, "url")
        assert hasattr(article, "word_count")
        assert hasattr(article, "source_type")
        assert article.word_count > 0
        assert article.text != ""


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_fetch_error_is_summarizer_error(self):
        from src.summarizer.exceptions import SummarizerError
        err = FetchError("test", url="https://example.com", status_code=404)
        assert isinstance(err, SummarizerError)
        assert err.status_code == 404
        assert err.url == "https://example.com"

    def test_parse_error_is_summarizer_error(self):
        from src.summarizer.exceptions import SummarizerError
        err = ParseError("test", source="file.html")
        assert isinstance(err, SummarizerError)
        assert err.source == "file.html"

    def test_fetch_error_str_includes_url(self):
        err = FetchError("HTTP error", url="https://example.com", status_code=404)
        s = str(err)
        assert "example.com" in s
        assert "404" in s

    def test_parse_error_str_includes_source(self):
        err = ParseError("Failed to parse", source="article.html")
        s = str(err)
        assert "article.html" in s

    def test_llm_error_is_summarizer_error(self):
        from src.summarizer.exceptions import SummarizerError, LLMError
        err = LLMError("API failed", model="gpt-4")
        assert isinstance(err, SummarizerError)
        assert "gpt-4" in str(err)

    def test_config_error_is_summarizer_error(self):
        from src.summarizer.exceptions import SummarizerError, ConfigError
        err = ConfigError("Missing API key")
        assert isinstance(err, SummarizerError)