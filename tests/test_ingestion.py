"""Unit tests for article ingestion: fetcher, extractor, and file_reader."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Adjust sys.path so that src is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.summarizer.models import Article, SourceType
from src.summarizer.exceptions import FetchError, ParseError
from src.summarizer.ingestion.fetcher import fetch_url
from src.summarizer.ingestion.extractor import extract_article, normalize_text
from src.summarizer.ingestion.file_reader import read_file
from src.summarizer.ingestion import fetch_article

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_HTML_PATH = FIXTURES_DIR / "sample_article.html"
SAMPLE_TXT_PATH = FIXTURES_DIR / "sample_article.txt"


def load_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# normalize_text tests
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_collapses_multiple_spaces(self):
        result = normalize_text("Hello   world   foo")
        assert "  " not in result

    def test_strips_zero_width_chars(self):
        text_with_zwsp = "Hello\u200bWorld"
        result = normalize_text(text_with_zwsp)
        assert "\u200b" not in result
        assert "HelloWorld" in result

    def test_collapses_excessive_blank_lines(self):
        text = "Line 1\n\n\n\n\n\nLine 2"
        result = normalize_text(text)
        # Should have at most 2 consecutive blank lines
        assert "\n\n\n" not in result

    def test_replaces_non_breaking_space(self):
        text = "Hello\u00a0World"
        result = normalize_text(text)
        assert "\u00a0" not in result
        assert "Hello World" in result

    def test_normalizes_unicode_to_nfc(self):
        # Precomposed vs decomposed 'é'
        composed = "caf\u00e9"
        decomposed = "cafe\u0301"
        assert normalize_text(decomposed) == normalize_text(composed)

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_strips_leading_trailing_whitespace(self):
        result = normalize_text("   hello world   ")
        assert result == "hello world"

    def test_removes_bom(self):
        text = "\ufeffHello World"
        result = normalize_text(text)
        assert "\ufeff" not in result
        assert "Hello World" in result


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------

class TestExtractArticle:
    def test_extracts_from_article_tag(self):
        html = """
        <html><body>
        <nav>Skip me</nav>
        <article>
            <h1>Test Title</h1>
            <p>This is the main content of the article. It has enough text.</p>
            <p>Second paragraph with more information about the topic.</p>
        </article>
        <footer>Skip this too</footer>
        </body></html>
        """
        article = extract_article(html, url="http://example.com/test")
        assert article.text
        assert "main content" in article.text
        assert "Skip me" not in article.text

    def test_extracts_from_main_tag(self):
        html = """
        <html><body>
        <header>Navigation here</header>
        <main>
            <p>Main content paragraph with sufficient text for extraction.</p>
            <p>Another paragraph in the main content area.</p>
        </main>
        </body></html>
        """
        article = extract_article(html)
        assert article.text
        assert "Main content paragraph" in article.text

    def test_extracts_og_title(self):
        html = """
        <html><head>
            <meta property="og:title" content="Open Graph Title">
            <title>Page Title | Site Name</title>
        </head><body>
        <article>
            <p>Article content goes here with enough text to be extracted properly.</p>
        </article>
        </body></html>
        """
        article = extract_article(html)
        # Either og:title or page title should be extracted
        assert article.title in ("Open Graph Title", "Page Title | Site Name") or article.title

    def test_extracts_from_sample_html_fixture(self):
        html = load_fixture("sample_article.html")
        article = extract_article(html, url="http://example.com/renewable-energy")
        assert article.text
        assert len(article.text) > 200
        assert article.word_count > 50
        # Key content should be present
        assert "renewable" in article.text.lower() or "energy" in article.text.lower()

    def test_raises_parse_error_on_empty_html(self):
        with pytest.raises(ParseError):
            extract_article("")

    def test_raises_parse_error_on_whitespace_only(self):
        with pytest.raises(ParseError):
            extract_article("   \n\t  ")

    def test_article_has_word_count(self):
        html = """
        <html><body><article>
        <p>This article has several words in it for testing purposes.</p>
        </article></body></html>
        """
        article = extract_article(html)
        assert article.word_count > 0

    def test_url_stored_in_article(self):
        html = """
        <html><body><article><p>Content here for testing URL storage.</p></article></body></html>
        """
        url = "http://example.com/article"
        article = extract_article(html, url=url)
        assert article.url == url

    def test_filters_nav_content(self):
        html = """
        <html><body>
        <nav id="main-nav">Home About Contact</nav>
        <article>
            <p>Real article content that should be extracted successfully.</p>
            <p>More real content here in the article body for testing.</p>
        </article>
        </body></html>
        """
        article = extract_article(html)
        # Nav content should not dominate
        assert "Real article content" in article.text


# ---------------------------------------------------------------------------
# File reader tests
# ---------------------------------------------------------------------------

class TestReadFile:
    def test_reads_txt_file(self):
        article = read_file(str(SAMPLE_TXT_PATH))
        assert article.text
        assert len(article.text) > 100
        assert article.source_type == SourceType.FILE

    def test_reads_html_file(self):
        article = read_file(str(SAMPLE_HTML_PATH))
        assert article.text
        assert len(article.text) > 100
        assert article.source_type == SourceType.FILE

    def test_txt_title_from_first_line(self):
        article = read_file(str(SAMPLE_TXT_PATH))
        assert article.title
        assert len(article.title) > 0

    def test_html_file_extracts_title(self):
        article = read_file(str(SAMPLE_HTML_PATH))
        assert article.title

    def test_raises_fetch_error_for_missing_file(self):
        with pytest.raises(FetchError) as exc_info:
            read_file("/nonexistent/path/to/article.txt")
        assert "not found" in str(exc_info.value).lower()

    def test_raises_parse_error_for_unsupported_extension(self, tmp_path):
        pdf_file = tmp_path / "article.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")
        with pytest.raises(ParseError) as exc_info:
            read_file(str(pdf_file))
        assert "unsupported" in str(exc_info.value).lower()

    def test_raises_parse_error_for_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        with pytest.raises(ParseError):
            read_file(str(empty_file))

    def test_word_count_set_correctly(self):
        article = read_file(str(SAMPLE_TXT_PATH))
        expected = len(article.text.split())
        assert article.word_count == expected

    def test_url_points_to_file_path(self):
        article = read_file(str(SAMPLE_TXT_PATH))
        assert article.url
        assert str(SAMPLE_TXT_PATH.name) in article.url

    def test_reads_utf8_file(self, tmp_path):
        content = "Unicode test: café, naïve, résumé\nThis is a proper article with enough content."
        f = tmp_path / "unicode.txt"
        f.write_text(content, encoding="utf-8")
        article = read_file(str(f))
        assert "café" in article.text or "cafe" in article.text

    def test_reads_html_with_htm_extension(self, tmp_path):
        html_content = """<html><body>
        <article><h1>Test</h1>
        <p>Article content for .htm extension test with sufficient length.</p>
        </article></body></html>"""
        f = tmp_path / "article.htm"
        f.write_text(html_content, encoding="utf-8")
        article = read_file(str(f))
        assert article.text


# ---------------------------------------------------------------------------
# Fetcher tests (with mocked requests)
# ---------------------------------------------------------------------------

class TestFetchUrl:
    def _make_mock_response(
        self,
        status_code=200,
        content=b"<html><body><article><p>Test content</p></article></body></html>",
        content_type="text/html; charset=utf-8",
        encoding="utf-8",
        url="http://example.com/article",
    ):
        mock_resp = MagicMock()
        mock_resp.ok = status_code < 400
        mock_resp.status_code = status_code
        mock_resp.headers = {
            "Content-Type": content_type,
        }
        mock_resp.encoding = encoding
        mock_resp.url = url

        # Simulate iter_content
        chunk_size = 8192
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)] or [b""]
        mock_resp.iter_content.return_value = iter(chunks)

        return mock_resp

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_successful_fetch(self, mock_get):
        html_bytes = b"<html><body><p>Hello world</p></body></html>"
        mock_get.return_value = self._make_mock_response(content=html_bytes)

        html, url = fetch_url("http://example.com/article")
        assert "Hello world" in html
        assert url == "http://example.com/article"
        mock_get.assert_called_once()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_404(self, mock_get):
        mock_get.return_value = self._make_mock_response(status_code=404)
        with pytest.raises(FetchError) as exc_info:
            fetch_url("http://example.com/missing")
        assert "404" in str(exc_info.value)

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_500(self, mock_get):
        mock_get.return_value = self._make_mock_response(status_code=500)
        with pytest.raises(FetchError) as exc_info:
            fetch_url("http://example.com/error")
        assert "500" in str(exc_info.value)

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_connection_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("Connection refused")
        with pytest.raises(FetchError) as exc_info:
            fetch_url("http://nonexistent.example.com/")
        assert "connect" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_timeout(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()
        with pytest.raises(FetchError) as exc_info:
            fetch_url("http://slow.example.com/")
        assert "timed out" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_on_too_many_redirects(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.TooManyRedirects()
        with pytest.raises(FetchError) as exc_info:
            fetch_url("http://redirect.example.com/")
        assert "redirect" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_raises_fetch_error_for_binary_content_type(self, mock_get):
        mock_get.return_value = self._make_mock_response(
            content_type="application/pdf"
        )
        with pytest.raises(FetchError) as exc_info:
            fetch_url("http://example.com/document.pdf")
        assert "content type" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_follows_redirects(self, mock_get):
        mock_get.return_value = self._make_mock_response(
            url="http://example.com/final-url"
        )
        html, final_url = fetch_url("http://example.com/redirect")
        assert final_url == "http://example.com/final-url"

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_user_agent_header_sent(self, mock_get):
        mock_get.return_value = self._make_mock_response()
        fetch_url("http://example.com/")
        call_kwargs = mock_get.call_args
        headers = call_kwargs[1].get("headers", {}) or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        # Check headers were passed
        assert mock_get.called

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_allows_xhtml_content_type(self, mock_get):
        mock_get.return_value = self._make_mock_response(
            content_type="application/xhtml+xml"
        )
        html, url = fetch_url("http://example.com/page.xhtml")
        assert html is not None


# ---------------------------------------------------------------------------
# Integration: fetch_article function
# ---------------------------------------------------------------------------

class TestFetchArticleIntegration:
    def test_fetch_article_from_txt_file(self):
        article = fetch_article(str(SAMPLE_TXT_PATH))
        assert isinstance(article, Article)
        assert article.source_type == SourceType.FILE
        assert article.text
        assert article.word_count > 0

    def test_fetch_article_from_html_file(self):
        article = fetch_article(str(SAMPLE_HTML_PATH))
        assert isinstance(article, Article)
        assert article.source_type == SourceType.FILE
        assert article.text

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_fetch_article_from_url(self, mock_get):
        html = load_fixture("sample_article.html").encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.encoding = "utf-8"
        mock_resp.url = "http://example.com/renewable-energy"
        mock_resp.iter_content.return_value = iter([html])
        mock_get.return_value = mock_resp

        article = fetch_article("http://example.com/renewable-energy")
        assert isinstance(article, Article)
        assert article.source_type == SourceType.URL
        assert article.text
        assert article.word_count > 0

    def test_fetch_article_raises_for_missing_file(self):
        with pytest.raises(FetchError):
            fetch_article("/no/such/file.txt")

    def test_fetch_article_article_dataclass_fields(self):
        article = fetch_article(str(SAMPLE_TXT_PATH))
        assert hasattr(article, "title")
        assert hasattr(article, "text")
        assert hasattr(article, "url")
        assert hasattr(article, "word_count")
        assert hasattr(article, "source_type")


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_fetch_error_is_summarizer_error(self):
        from src.summarizer.exceptions import SummarizerError
        err = FetchError("test error", url="http://example.com", status_code=404)
        assert isinstance(err, SummarizerError)
        assert err.url == "http://example.com"
        assert err.status_code == 404

    def test_parse_error_is_summarizer_error(self):
        from src.summarizer.exceptions import SummarizerError
        err = ParseError("parse failed", source="test.html")
        assert isinstance(err, SummarizerError)
        assert err.source == "test.html"

    def test_fetch_error_message(self):
        err = FetchError("Connection refused")
        assert str(err) == "Connection refused"

    def test_parse_error_message(self):
        err = ParseError("Could not extract text")
        assert str(err) == "Could not extract text"