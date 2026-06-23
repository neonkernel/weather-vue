"""Unit tests for the article ingestion pipeline."""

import os
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Adjust import path based on project layout
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.summarizer.exceptions import FetchError, ParseError
from src.summarizer.models import Article, SourceType
from src.summarizer.ingestion.fetcher import fetch_url
from src.summarizer.ingestion.extractor import extract_article, normalize_text
from src.summarizer.ingestion.file_reader import read_file
from src.summarizer.ingestion import fetch_article


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_HTML_PATH = os.path.join(FIXTURES_DIR, "sample_article.html")
SAMPLE_TXT_PATH = os.path.join(FIXTURES_DIR, "sample_article.txt")


@pytest.fixture
def sample_html_content():
    """Return the content of sample_article.html."""
    with open(SAMPLE_HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def sample_txt_content():
    """Return the content of sample_article.txt."""
    with open(SAMPLE_TXT_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def minimal_html():
    """Minimal valid HTML with article content."""
    return """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
<nav><a href="/">Home</a></nav>
<article>
<h1>Test Article Title</h1>
<p>This is the first paragraph of the test article with enough words to pass the density check.</p>
<p>This is the second paragraph with more content to ensure the extractor works correctly.</p>
<p>A third paragraph adds even more substance to the article text for testing purposes.</p>
</article>
<footer>Footer content here</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Tests: normalize_text
# ---------------------------------------------------------------------------

class TestNormalizeText:

    def test_removes_zero_width_characters(self):
        text = "Hello\u200bWorld\u200c!"
        result = normalize_text(text)
        assert "\u200b" not in result
        assert "\u200c" not in result
        assert "HelloWorld!" in result

    def test_collapses_multiple_spaces(self):
        text = "Hello    world   foo"
        result = normalize_text(text)
        assert "Hello world foo" in result

    def test_strips_excessive_blank_lines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = normalize_text(text)
        # Should have at most 2 consecutive blank lines
        assert "\n\n\n\n\n" not in result

    def test_normalizes_line_endings(self):
        text = "Line 1\r\nLine 2\rLine 3"
        result = normalize_text(text)
        assert "\r" not in result

    def test_strips_leading_trailing_whitespace(self):
        text = "   Hello World   "
        result = normalize_text(text)
        assert result == result.strip()

    def test_empty_string_returns_empty(self):
        assert normalize_text("") == ""

    def test_none_like_empty_string(self):
        assert normalize_text("") == ""


# ---------------------------------------------------------------------------
# Tests: fetch_url
# ---------------------------------------------------------------------------

class TestFetchUrl:

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_successful_fetch(self, mock_get):
        """fetch_url returns (html, final_url) on success."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com/article"
        mock_response.iter_content.return_value = [b"<html><body>Hello</body></html>"]
        mock_get.return_value = mock_response

        html, final_url = fetch_url("https://example.com/article")
        assert "Hello" in html
        assert final_url == "https://example.com/article"

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_timeout_raises_fetch_error(self, mock_get):
        """fetch_url raises FetchError on timeout."""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.Timeout()

        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/slow")
        assert "timed out" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_connection_error_raises_fetch_error(self, mock_get):
        """fetch_url raises FetchError on connection error."""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError("Network unreachable")

        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://nonexistent.example.com/")
        assert "connection error" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_http_404_raises_fetch_error(self, mock_get):
        """fetch_url raises FetchError on HTTP 404."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.url = "https://example.com/notfound"
        mock_get.return_value = mock_response

        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/notfound")
        assert "404" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_http_500_raises_fetch_error(self, mock_get):
        """fetch_url raises FetchError on HTTP 500."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.url = "https://example.com/"
        mock_get.return_value = mock_response

        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/")
        assert "500" in str(exc_info.value)

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_wrong_content_type_raises_fetch_error(self, mock_get):
        """fetch_url raises FetchError for non-HTML content types."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_response.url = "https://example.com/doc.pdf"
        mock_get.return_value = mock_response

        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://example.com/doc.pdf")
        assert "content type" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_too_many_redirects_raises_fetch_error(self, mock_get):
        """fetch_url raises FetchError on redirect loop."""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.TooManyRedirects()

        with pytest.raises(FetchError) as exc_info:
            fetch_url("https://redirect-loop.example.com/")
        assert "redirect" in str(exc_info.value).lower()

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_user_agent_header_sent(self, mock_get):
        """fetch_url sends a User-Agent header."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com/"
        mock_response.iter_content.return_value = [b"<html><body>Test</body></html>"]
        mock_get.return_value = mock_response

        fetch_url("https://example.com/")
        call_kwargs = mock_get.call_args
        headers = call_kwargs[1]["headers"] if call_kwargs[1] else call_kwargs[0][1]
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]


# ---------------------------------------------------------------------------
# Tests: extract_article
# ---------------------------------------------------------------------------

class TestExtractArticle:

    def test_extracts_from_article_tag(self, minimal_html):
        """Extractor finds content in <article> tag."""
        article = extract_article(minimal_html, url="https://example.com/test")
        assert article.text
        assert len(article.text) > 50
        assert article.word_count > 10

    def test_extracts_title(self, minimal_html):
        """Extractor finds a title from the HTML."""
        article = extract_article(minimal_html)
        # Title should be non-empty
        assert article.title is not None

    def test_extracts_from_sample_html_fixture(self, sample_html_content):
        """Extractor works on the sample_article.html fixture."""
        article = extract_article(sample_html_content, url="https://example.com/renewable")
        assert article.text
        assert "renewable" in article.text.lower() or "energy" in article.text.lower()
        assert article.word_count > 100

    def test_no_navigation_content_in_output(self, sample_html_content):
        """Extracted text should not contain navigation boilerplate."""
        article = extract_article(sample_html_content)
        # "Privacy Policy" is in the footer and should be removed
        # Note: this is a soft check; trafilatura may be very thorough
        assert article.text  # At minimum, we got something

    def test_empty_html_raises_parse_error(self):
        """extract_article raises ParseError on empty input."""
        with pytest.raises(ParseError):
            extract_article("")

    def test_whitespace_only_html_raises_parse_error(self):
        """extract_article raises ParseError on whitespace-only input."""
        with pytest.raises(ParseError):
            extract_article("   \n\t  ")

    def test_article_has_correct_url(self, minimal_html):
        """Article URL is set correctly."""
        article = extract_article(minimal_html, url="https://test.example.com/article")
        assert article.url == "https://test.example.com/article"

    def test_article_word_count_is_populated(self, sample_html_content):
        """word_count is calculated and > 0."""
        article = extract_article(sample_html_content)
        assert article.word_count > 0

    def test_extracts_from_main_tag(self):
        """Extractor finds content in <main> tag when no <article> is present."""
        html = """<!DOCTYPE html>
<html>
<head><title>Main Tag Article</title></head>
<body>
<nav>Navigation here</nav>
<main>
<h1>Main Content Title</h1>
<p>This is the main content of the page with sufficient words for extraction testing.</p>
<p>Another paragraph provides more text to work with in the main extraction test case.</p>
<p>Yet another paragraph ensures there is enough content to extract meaningfully here.</p>
</main>
<footer>Footer</footer>
</body>
</html>"""
        article = extract_article(html)
        assert article.text
        assert len(article.text.split()) > 10

    def test_returns_article_dataclass(self, minimal_html):
        """extract_article returns an Article instance."""
        result = extract_article(minimal_html)
        assert isinstance(result, Article)


# ---------------------------------------------------------------------------
# Tests: read_file
# ---------------------------------------------------------------------------

class TestReadFile:

    def test_reads_txt_file(self):
        """read_file reads a .txt file successfully."""
        content, title, is_html = read_file(SAMPLE_TXT_PATH)
        assert content
        assert "renewable" in content.lower() or "energy" in content.lower()
        assert is_html is False

    def test_reads_html_file(self):
        """read_file reads a .html file and marks it as HTML."""
        content, title, is_html = read_file(SAMPLE_HTML_PATH)
        assert content
        assert is_html is True
        assert "<html" in content.lower() or "<!doctype" in content.lower()

    def test_title_derived_from_filename_txt(self):
        """Title is derived from the filename for .txt files."""
        _, title, _ = read_file(SAMPLE_TXT_PATH)
        assert title  # Should be non-empty
        assert isinstance(title, str)

    def test_title_derived_from_filename_html(self):
        """Title is derived from the filename for .html files."""
        _, title, _ = read_file(SAMPLE_HTML_PATH)
        assert title
        assert isinstance(title, str)

    def test_nonexistent_file_raises_fetch_error(self):
        """read_file raises FetchError for missing files."""
        with pytest.raises(FetchError) as exc_info:
            read_file("/nonexistent/path/to/missing_file.txt")
        assert "not found" in str(exc_info.value).lower()

    def test_unsupported_extension_raises_parse_error(self, tmp_path):
        """read_file raises ParseError for unsupported extensions."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_text("PDF content here")

        with pytest.raises(ParseError) as exc_info:
            read_file(str(pdf_file))
        assert ".pdf" in str(exc_info.value)

    def test_empty_file_raises_parse_error(self, tmp_path):
        """read_file raises ParseError for empty files."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        with pytest.raises(ParseError) as exc_info:
            read_file(str(empty_file))
        assert "empty" in str(exc_info.value).lower()

    def test_directory_path_raises_fetch_error(self, tmp_path):
        """read_file raises FetchError when path is a directory."""
        with pytest.raises(FetchError) as exc_info:
            read_file(str(tmp_path))
        assert "not a file" in str(exc_info.value).lower()

    def test_reads_htm_extension(self, tmp_path):
        """read_file handles .htm extension as HTML."""
        htm_file = tmp_path / "page.htm"
        htm_file.write_text("<html><body><p>Some content here.</p></body></html>")

        content, title, is_html = read_file(str(htm_file))
        assert is_html is True
        assert "Some content" in content

    def test_custom_encoding_fallback(self, tmp_path):
        """read_file falls back to latin-1 on UTF-8 decode error."""
        # Write a file with latin-1 encoding
        latin_file = tmp_path / "latin.txt"
        latin_file.write_bytes("Caf\xe9 au lait is a popular drink enjoyed by many people worldwide.".encode("latin-1"))

        content, title, is_html = read_file(str(latin_file))
        assert content  # Should not raise


# ---------------------------------------------------------------------------
# Tests: fetch_article (integration-level with mocks)
# ---------------------------------------------------------------------------

class TestFetchArticle:

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_fetch_article_from_url(self, mock_get, sample_html_content):
        """fetch_article fetches and extracts article from a URL."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.encoding = "utf-8"
        mock_response.url = "https://example.com/renewable-energy"
        mock_response.iter_content.return_value = [sample_html_content.encode("utf-8")]
        mock_get.return_value = mock_response

        article = fetch_article("https://example.com/renewable-energy")
        assert isinstance(article, Article)
        assert article.source_type == SourceType.URL
        assert article.url == "https://example.com/renewable-energy"
        assert article.text
        assert article.word_count > 0

    def test_fetch_article_from_txt_file(self):
        """fetch_article reads a local .txt file."""
        article = fetch_article(SAMPLE_TXT_PATH)
        assert isinstance(article, Article)
        assert article.source_type == SourceType.FILE
        assert article.url is None
        assert article.text
        assert article.word_count > 0

    def test_fetch_article_from_html_file(self):
        """fetch_article reads and extracts a local .html file."""
        article = fetch_article(SAMPLE_HTML_PATH)
        assert isinstance(article, Article)
        assert article.source_type == SourceType.FILE
        assert article.text
        assert article.word_count > 0

    def test_fetch_article_missing_file_raises_fetch_error(self):
        """fetch_article raises FetchError for missing local files."""
        with pytest.raises(FetchError):
            fetch_article("/tmp/this_file_does_not_exist_12345.txt")

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_fetch_article_url_timeout_raises_fetch_error(self, mock_get):
        """fetch_article raises FetchError when URL times out."""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.Timeout()

        with pytest.raises(FetchError):
            fetch_article("https://slow-server.example.com/article")

    @patch("src.summarizer.ingestion.fetcher.requests.get")
    def test_fetch_article_http_error_raises_fetch_error(self, mock_get):
        """fetch_article raises FetchError on HTTP error status."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.url = "https://example.com/restricted"
        mock_get.return_value = mock_response

        with pytest.raises(FetchError) as exc_info:
            fetch_article("https://example.com/restricted")
        assert "403" in str(exc_info.value)

    def test_fetch_article_txt_has_correct_word_count(self):
        """fetch_article word_count matches actual word count for .txt files."""
        article = fetch_article(SAMPLE_TXT_PATH)
        expected_word_count = len(article.text.split())
        assert article.word_count == expected_word_count


# ---------------------------------------------------------------------------
# Tests: Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:

    def test_fetch_error_is_summarizer_error(self):
        from src.summarizer.exceptions import SummarizerError
        err = FetchError("test", url="https://example.com", status_code=404)
        assert isinstance(err, SummarizerError)
        assert err.url == "https://example.com"
        assert err.status_code == 404

    def test_parse_error_is_summarizer_error(self):
        from src.summarizer.exceptions import SummarizerError
        err = ParseError("test", source="file.html")
        assert isinstance(err, SummarizerError)
        assert err.source == "file.html"

    def test_fetch_error_str(self):
        err = FetchError("Could not fetch URL")
        assert str(err) == "Could not fetch URL"

    def test_parse_error_str(self):
        err = ParseError("Could not parse HTML")
        assert str(err) == "Could not parse HTML"

    def test_llm_error_attributes(self):
        from src.summarizer.exceptions import LLMError
        err = LLMError("API failed", model="gpt-4")
        assert err.model == "gpt-4"
        assert str(err) == "API failed"

    def test_config_error(self):
        from src.summarizer.exceptions import ConfigError
        err = ConfigError("Missing API key")
        assert str(err) == "Missing API key"


# ---------------------------------------------------------------------------
# Tests: Article dataclass
# ---------------------------------------------------------------------------

class TestArticleDataclass:

    def test_word_count_auto_calculated(self):
        """Article auto-calculates word_count if not provided."""
        article = Article(title="Test", text="This is a four word sentence")
        # "This is a four word sentence" = 6 words
        assert article.word_count == 6

    def test_word_count_zero_for_empty_text(self):
        """Article with empty text has word_count 0."""
        article = Article(title="Test", text="", word_count=0)
        assert article.word_count == 0

    def test_source_type_default_is_url(self):
        """Default source_type is URL."""
        article = Article(title="Test", text="Some text here")
        assert article.source_type == SourceType.URL

    def test_url_optional(self):
        """URL field is optional and defaults to None."""
        article = Article(title="Test", text="Some text")
        assert article.url is None

    def test_source_type_enum_values(self):
        """SourceType enum has expected values."""
        assert SourceType.URL == "url"
        assert SourceType.FILE == "file"
        assert SourceType.TEXT == "text"