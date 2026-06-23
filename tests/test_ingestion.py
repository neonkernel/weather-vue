"""Unit tests for the article ingestion pipeline."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_HTML = FIXTURES_DIR / "sample_article.html"
SAMPLE_TXT = FIXTURES_DIR / "sample_article.txt"


# ===========================================================================
# Helpers
# ===========================================================================

def _make_response(
    status_code: int = 200,
    content: bytes = b"<html><body><article><p>Hello world article text here for testing purposes with enough content.</p></article></body></html>",
    content_type: str = "text/html; charset=utf-8",
    encoding: str = "utf-8",
    url: str = "https://example.com/article",
):
    """Build a mock requests.Response object."""
    response = MagicMock()
    response.status_code = status_code
    response.url = url
    response.encoding = encoding
    response.headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(content)),
    }
    response.iter_content = MagicMock(return_value=iter([content]))

    def raise_for_status():
        if status_code >= 400:
            from requests.exceptions import HTTPError
            raise HTTPError(f"HTTP {status_code}", response=response)

    response.raise_for_status = raise_for_status
    return response


# ===========================================================================
# Fetcher tests
# ===========================================================================

class TestFetchUrl:
    """Tests for src.summarizer.ingestion.fetcher.fetch_url"""

    def test_successful_fetch(self):
        from src.summarizer.ingestion.fetcher import fetch_url

        mock_response = _make_response()
        with patch("requests.get", return_value=mock_response):
            html, final_url = fetch_url("https://example.com/article")

        assert "Hello world" in html
        assert final_url == "https://example.com/article"

    def test_timeout_raises_fetch_error(self):
        from requests.exceptions import ReadTimeout
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        with patch("requests.get", side_effect=ReadTimeout("timed out")):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/slow")

        assert "timed out" in str(exc_info.value).lower()
        assert exc_info.value.source == "https://example.com/slow"

    def test_connection_error_raises_fetch_error(self):
        from requests.exceptions import ConnectionError as ReqConnError
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        with patch("requests.get", side_effect=ReqConnError("no route")):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://unreachable.example.com/")

        assert exc_info.value.source == "https://unreachable.example.com/"

    def test_http_404_raises_fetch_error(self):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        mock_response = _make_response(status_code=404)
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/missing")

        assert exc_info.value.status_code == 404

    def test_http_500_raises_fetch_error(self):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        mock_response = _make_response(status_code=500)
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/error")

        assert exc_info.value.status_code == 500

    def test_unsupported_content_type_raises_fetch_error(self):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        mock_response = _make_response(content_type="application/pdf")
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/doc.pdf")

        assert "content type" in str(exc_info.value).lower()

    def test_too_many_redirects_raises_fetch_error(self):
        from requests.exceptions import TooManyRedirects
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        with patch("requests.get", side_effect=TooManyRedirects("redirect loop")):
            with pytest.raises(FetchError):
                fetch_url("https://redirect-loop.example.com/")

    def test_returns_decoded_html(self):
        from src.summarizer.ingestion.fetcher import fetch_url

        html_bytes = "<html><body><p>Encoded content</p></body></html>".encode("utf-8")
        mock_response = _make_response(content=html_bytes, encoding="utf-8")
        with patch("requests.get", return_value=mock_response):
            html, _ = fetch_url("https://example.com/")

        assert isinstance(html, str)
        assert "Encoded content" in html


# ===========================================================================
# Extractor tests
# ===========================================================================

class TestExtractTextFromHtml:
    """Tests for src.summarizer.ingestion.extractor.extract_text_from_html"""

    def test_extracts_article_tag_content(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html

        html = """
        <html><body>
          <nav>Navigation junk that should be ignored completely</nav>
          <article>
            <h1>My Article</h1>
            <p>This is the main content of the article with enough words to pass validation.</p>
            <p>Second paragraph with more interesting details about the topic at hand.</p>
          </article>
          <footer>Footer junk ignored</footer>
        </body></html>
        """
        title, text = extract_text_from_html(html)
        assert "main content" in text.lower()
        assert "navigation junk" not in text.lower()
        assert "footer junk" not in text.lower()

    def test_extracts_title_from_og_tag(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html

        html = """
        <html><head>
          <meta property="og:title" content="Open Graph Title">
          <title>Page Title | Site Name</title>
        </head><body>
          <article><p>Content here with sufficient length for extraction tests.</p></article>
        </body></html>
        """
        title, text = extract_text_from_html(html)
        assert title == "Open Graph Title"

    def test_extracts_title_from_h1_fallback(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html

        html = """
        <html><head><title>Page Title</title></head><body>
          <article>
            <h1>Article Heading</h1>
            <p>Content here with sufficient words for extraction and testing purposes.</p>
          </article>
        </body></html>
        """
        title, text = extract_text_from_html(html)
        assert title == "Article Heading"

    def test_raises_parse_error_on_empty_html(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html
        from src.summarizer.exceptions import ParseError

        with pytest.raises(ParseError):
            extract_text_from_html("")

    def test_raises_parse_error_on_whitespace_only(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html
        from src.summarizer.exceptions import ParseError

        with pytest.raises(ParseError):
            extract_text_from_html("   \n\t  ")

    def test_strips_script_and_style_tags(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html

        html = """
        <html><body>
          <script>var x = 1; function doSomething() { return true; }</script>
          <style>.foo { color: red; display: none; }</style>
          <article>
            <p>Real article content here with plenty of words for threshold testing.</p>
            <p>More real content in this paragraph to ensure we meet word count requirements.</p>
          </article>
        </body></html>
        """
        title, text = extract_text_from_html(html)
        assert "var x" not in text
        assert "color: red" not in text
        assert "Real article content" in text

    def test_extracts_from_sample_html_fixture(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html

        html = SAMPLE_HTML.read_text(encoding="utf-8")
        title, text = extract_text_from_html(html)

        assert "renewable energy" in text.lower()
        assert "battery" in text.lower()
        assert len(text.split()) > 100

    def test_title_extracted_from_sample_fixture(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html

        html = SAMPLE_HTML.read_text(encoding="utf-8")
        title, text = extract_text_from_html(html)

        assert "Renewable Energy" in title

    def test_sidebar_content_excluded(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html

        html = SAMPLE_HTML.read_text(encoding="utf-8")
        _, text = extract_text_from_html(html)

        # The sidebar links should not appear in the extracted text
        assert "Solar Power Trends" not in text

    def test_uses_main_tag_when_no_article(self):
        from src.summarizer.ingestion.extractor import extract_text_from_html

        html = """
        <html><body>
          <nav>Navigation content to ignore</nav>
          <main>
            <p>Primary main content that should be extracted by the heuristic.</p>
            <p>Secondary paragraph with more details and words to meet the threshold.</p>
            <p>Third paragraph ensures we have enough words for validation to pass.</p>
          </main>
        </body></html>
        """
        title, text = extract_text_from_html(html)
        assert "Primary main content" in text


class TestNormalizeText:
    """Tests for src.summarizer.ingestion.extractor.normalize_text"""

    def test_collapses_multiple_spaces(self):
        from src.summarizer.ingestion.extractor import normalize_text

        result = normalize_text("Hello    world   foo")
        assert "  " not in result
        assert "Hello world foo" in result

    def test_removes_zero_width_chars(self):
        from src.summarizer.ingestion.extractor import normalize_text

        text = "Hello\u200bWorld\u200c!"
        result = normalize_text(text)
        assert "\u200b" not in result
        assert "\u200c" not in result

    def test_collapses_excessive_blank_lines(self):
        from src.summarizer.ingestion.extractor import normalize_text

        text = "Para one\n\n\n\n\nPara two"
        result = normalize_text(text)
        assert "\n\n\n" not in result

    def test_strips_leading_trailing_whitespace(self):
        from src.summarizer.ingestion.extractor import normalize_text

        result = normalize_text("\n\n  Hello World  \n\n")
        assert result == "Hello World"

    def test_handles_empty_string(self):
        from src.summarizer.ingestion.extractor import normalize_text

        assert normalize_text("") == ""

    def test_replaces_nbsp(self):
        from src.summarizer.ingestion.extractor import normalize_text

        text = "Hello\xa0World"
        result = normalize_text(text)
        assert "\xa0" not in result


# ===========================================================================
# File reader tests
# ===========================================================================

class TestReadFile:
    """Tests for src.summarizer.ingestion.file_reader.read_file"""

    def test_reads_txt_file(self):
        from src.summarizer.ingestion.file_reader import read_file

        title, content, file_uri = read_file(str(SAMPLE_TXT))

        assert "renewable energy" in content.lower()
        assert title == "sample_article"
        assert file_uri.startswith("file://")

    def test_reads_html_file(self):
        from src.summarizer.ingestion.file_reader import read_file

        title, content, file_uri = read_file(str(SAMPLE_HTML))

        assert "<article" in content
        assert title == "sample_article"

    def test_file_not_found_raises_fetch_error(self):
        from src.summarizer.ingestion.file_reader import read_file
        from src.summarizer.exceptions import FetchError

        with pytest.raises(FetchError) as exc_info:
            read_file("/nonexistent/path/to/article.txt")

        assert "not found" in str(exc_info.value).lower()

    def test_unsupported_extension_raises_fetch_error(self):
        from src.summarizer.ingestion.file_reader import read_file
        from src.summarizer.exceptions import FetchError

        # Create a temp file with unsupported extension
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"PDF content")
            tmp_path = f.name

        try:
            with pytest.raises(FetchError) as exc_info:
                read_file(tmp_path)
            assert "unsupported" in str(exc_info.value).lower()
        finally:
            os.unlink(tmp_path)

    def test_directory_path_raises_fetch_error(self):
        from src.summarizer.ingestion.file_reader import read_file
        from src.summarizer.exceptions import FetchError

        # Passing a directory instead of a file
        with pytest.raises(FetchError):
            read_file(str(FIXTURES_DIR))

    def test_empty_file_raises_parse_error(self):
        from src.summarizer.ingestion.file_reader import read_file
        from src.summarizer.exceptions import ParseError

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("   \n  \n  ")
            tmp_path = f.name

        try:
            with pytest.raises(ParseError):
                read_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_returns_file_uri(self):
        from src.summarizer.ingestion.file_reader import read_file

        title, content, file_uri = read_file(str(SAMPLE_TXT))
        assert file_uri.startswith("file:///")

    def test_latin1_fallback_encoding(self):
        from src.summarizer.ingestion.file_reader import read_file

        import tempfile
        # Write a file with latin-1 encoding (not valid UTF-8)
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write("Caf\xe9 au lait is delicious and worth reading about.\n".encode("latin-1"))
            tmp_path = f.name

        try:
            title, content, file_uri = read_file(tmp_path)
            assert "Caf" in content
        finally:
            os.unlink(tmp_path)


# ===========================================================================
# Pipeline integration tests
# ===========================================================================

class TestFetchArticle:
    """Integration tests for the public fetch_article function."""

    def test_fetch_article_from_url(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.models import SourceType

        long_html = """
        <html><body><article>
          <h1>Test Article Title</h1>
          <p>This is a long article with lots of content to ensure extraction works.
          We need many words here to pass all the validation thresholds that have been
          set up in the extraction pipeline. More words make for better tests indeed.</p>
          <p>Second paragraph adds more depth to the article making it realistic and
          ensuring the word count exceeds the minimum required threshold for success.</p>
        </article></body></html>
        """.encode("utf-8")

        mock_response = _make_response(content=long_html)
        with patch("requests.get", return_value=mock_response):
            article = fetch_article("https://example.com/article")

        assert article.source_type == SourceType.URL
        assert article.url == "https://example.com/article"
        assert article.word_count > 0
        assert len(article.text) > 0

    def test_fetch_article_from_txt_file(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.models import SourceType

        article = fetch_article(str(SAMPLE_TXT))

        assert article.source_type == SourceType.FILE
        assert "renewable energy" in article.text.lower()
        assert article.word_count > 50
        assert article.url.startswith("file://")

    def test_fetch_article_from_html_file(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.models import SourceType

        article = fetch_article(str(SAMPLE_HTML))

        assert article.source_type == SourceType.FILE
        assert "renewable energy" in article.text.lower()
        assert article.word_count > 50

    def test_fetch_article_url_404_raises_fetch_error(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.exceptions import FetchError

        mock_response = _make_response(status_code=404)
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(FetchError):
                fetch_article("https://example.com/missing")

    def test_fetch_article_nonexistent_file_raises_fetch_error(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.exceptions import FetchError

        with pytest.raises(FetchError):
            fetch_article("/no/such/file.txt")

    def test_article_word_count_is_computed(self):
        from src.summarizer.ingestion import fetch_article

        article = fetch_article(str(SAMPLE_TXT))
        expected = len(article.text.split())
        assert article.word_count == expected

    def test_article_title_populated_from_html_file(self):
        from src.summarizer.ingestion import fetch_article

        article = fetch_article(str(SAMPLE_HTML))
        assert article.title != ""
        assert article.title != "Untitled"


# ===========================================================================
# Exception hierarchy tests
# ===========================================================================

class TestExceptions:
    """Tests for the custom exception hierarchy."""

    def test_fetch_error_is_summarizer_error(self):
        from src.summarizer.exceptions import FetchError, SummarizerError

        exc = FetchError("test", source="http://x.com", status_code=404)
        assert isinstance(exc, SummarizerError)
        assert exc.source == "http://x.com"
        assert exc.status_code == 404

    def test_parse_error_is_summarizer_error(self):
        from src.summarizer.exceptions import ParseError, SummarizerError

        exc = ParseError("test", source="file://x.txt")
        assert isinstance(exc, SummarizerError)
        assert exc.source == "file://x.txt"

    def test_llm_error_stores_model(self):
        from src.summarizer.exceptions import LLMError

        exc = LLMError("api failed", model="gpt-4")
        assert exc.model == "gpt-4"

    def test_config_error_stores_key(self):
        from src.summarizer.exceptions import ConfigError

        exc = ConfigError("missing key", key="OPENAI_API_KEY")
        assert exc.key == "OPENAI_API_KEY"

    def test_cause_is_stored(self):
        from src.summarizer.exceptions import FetchError

        original = ValueError("original error")
        exc = FetchError("wrapper", cause=original)
        assert exc.cause is original

    def test_str_includes_cause(self):
        from src.summarizer.exceptions import FetchError

        cause = ConnectionError("network down")
        exc = FetchError("could not fetch", cause=cause)
        assert "network down" in str(exc)


# ===========================================================================
# Article model tests
# ===========================================================================

class TestArticleModel:
    """Tests for the Article dataclass."""

    def test_word_count_auto_computed(self):
        from src.summarizer.models import Article

        article = Article(title="Test", text="one two three four five")
        assert article.word_count == 5

    def test_explicit_word_count_not_overridden(self):
        from src.summarizer.models import Article

        article = Article(title="Test", text="one two three", word_count=99)
        # __post_init__ only sets word_count if it is 0
        assert article.word_count == 99

    def test_source_type_defaults_to_text(self):
        from src.summarizer.models import Article, SourceType

        article = Article(title="T", text="some text content here")
        assert article.source_type == SourceType.TEXT

    def test_url_defaults_to_none(self):
        from src.summarizer.models import Article

        article = Article(title="T", text="some text")
        assert article.url is None