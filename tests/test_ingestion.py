"""Unit tests for article ingestion: fetcher, extractor, and file_reader."""

import os
import pytest
from unittest.mock import MagicMock, patch, mock_open

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_HTML_PATH = os.path.join(FIXTURES_DIR, "sample_article.html")
SAMPLE_TXT_PATH = os.path.join(FIXTURES_DIR, "sample_article.txt")


def _load_fixture(filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_html() -> str:
    return _load_fixture("sample_article.html")


@pytest.fixture
def sample_txt() -> str:
    return _load_fixture("sample_article.txt")


@pytest.fixture
def minimal_html() -> str:
    return """
    <html>
    <head><title>Test Article</title></head>
    <body>
    <nav><a href="/">Home</a><a href="/about">About</a></nav>
    <article>
        <h1>Test Article Heading</h1>
        <p>This is the first paragraph of the test article. It contains enough words to pass
        the minimum word count check for extraction to succeed properly.</p>
        <p>This is a second paragraph with more content about the topic being discussed in this
        sample article that is used for unit testing the extraction logic in our application.</p>
        <p>And a third paragraph to make absolutely sure we have sufficient content for the
        heuristic extractor to consider this a valid article worth returning to the caller.</p>
    </article>
    <footer><p>Copyright 2026</p></footer>
    <script>console.log("noise");</script>
    </body>
    </html>
    """


@pytest.fixture
def mock_response():
    """Factory for creating mock requests.Response objects."""
    def _make_response(
        status_code=200,
        content=b"<html><body><article><p>Hello world content for testing purposes and making sure we have enough words.</p></article></body></html>",
        content_type="text/html; charset=utf-8",
        url="https://example.com/article",
        encoding="utf-8",
    ):
        response = MagicMock()
        response.status_code = status_code
        response.url = url
        response.encoding = encoding
        response.apparent_encoding = encoding
        response.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(content)),
        }
        # iter_content yields chunks
        response.iter_content = MagicMock(
            return_value=iter([content])
        )
        # raise_for_status behavior
        if status_code >= 400:
            import requests
            http_err = requests.HTTPError(f"{status_code} Error")
            http_err.response = response
            response.raise_for_status = MagicMock(side_effect=http_err)
        else:
            response.raise_for_status = MagicMock(return_value=None)
        return response
    return _make_response


# ===========================================================================
# Tests: exceptions
# ===========================================================================

class TestExceptions:
    def test_fetch_error_str_with_url(self):
        from src.summarizer.exceptions import FetchError
        err = FetchError("Could not fetch", url="https://example.com")
        assert "https://example.com" in str(err)
        assert "Could not fetch" in str(err)

    def test_fetch_error_str_without_url(self):
        from src.summarizer.exceptions import FetchError
        err = FetchError("Could not fetch")
        assert "Could not fetch" in str(err)

    def test_fetch_error_with_cause(self):
        from src.summarizer.exceptions import FetchError
        cause = ValueError("original error")
        err = FetchError("Wrapper error", cause=cause)
        assert "original error" in str(err)

    def test_parse_error(self):
        from src.summarizer.exceptions import ParseError
        err = ParseError("Bad HTML")
        assert "Bad HTML" in str(err)

    def test_llm_error(self):
        from src.summarizer.exceptions import LLMError
        err = LLMError("API failed", model="gpt-4")
        assert "API failed" in str(err)
        assert err.model == "gpt-4"

    def test_config_error(self):
        from src.summarizer.exceptions import ConfigError
        err = ConfigError("Missing key", key="OPENAI_API_KEY")
        assert "Missing key" in str(err)
        assert err.key == "OPENAI_API_KEY"

    def test_exception_hierarchy(self):
        from src.summarizer.exceptions import (
            SummarizerError, FetchError, ParseError, LLMError, ConfigError
        )
        for exc_cls in [FetchError, ParseError, LLMError, ConfigError]:
            assert issubclass(exc_cls, SummarizerError)
            assert issubclass(exc_cls, Exception)


# ===========================================================================
# Tests: models
# ===========================================================================

class TestModels:
    def test_article_from_text(self):
        from src.summarizer.models import Article, SourceType
        article = Article.from_text(
            text="Hello world this is a test article with some words.",
            title="Test Article",
            url="https://example.com",
            source_type=SourceType.URL,
        )
        assert article.title == "Test Article"
        assert article.url == "https://example.com"
        assert article.word_count == 10
        assert article.source_type == SourceType.URL

    def test_article_word_count_empty(self):
        from src.summarizer.models import Article
        article = Article.from_text(text="")
        assert article.word_count == 0

    def test_article_word_count_whitespace(self):
        from src.summarizer.models import Article
        article = Article.from_text(text="   one   two   three   ")
        assert article.word_count == 3

    def test_summary_total_tokens(self):
        from src.summarizer.models import Article, Summary, SourceType
        article = Article.from_text("Some text here.", title="Test")
        summary = Summary(
            article=article,
            summary_text="Brief summary.",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert summary.total_tokens == 150

    def test_source_type_values(self):
        from src.summarizer.models import SourceType
        assert SourceType.URL == "url"
        assert SourceType.FILE == "file"
        assert SourceType.TEXT == "text"


# ===========================================================================
# Tests: fetcher
# ===========================================================================

class TestFetcher:
    def test_fetch_url_success(self, mock_response):
        from src.summarizer.ingestion.fetcher import fetch_url

        response = mock_response(
            status_code=200,
            content=b"<html><body><p>Article content here for testing.</p></body></html>",
            url="https://example.com/article",
        )

        with patch("src.summarizer.ingestion.fetcher.requests.get", return_value=response):
            html, final_url = fetch_url("https://example.com/article")

        assert "Article content" in html
        assert final_url == "https://example.com/article"

    def test_fetch_url_http_error(self, mock_response):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        response = mock_response(status_code=404, url="https://example.com/missing")

        with patch("src.summarizer.ingestion.fetcher.requests.get", return_value=response):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/missing")

        assert "404" in str(exc_info.value)

    def test_fetch_url_timeout(self):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError
        from requests.exceptions import ReadTimeout

        with patch(
            "src.summarizer.ingestion.fetcher.requests.get",
            side_effect=ReadTimeout("timed out"),
        ):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/slow")

        assert "timed out" in str(exc_info.value).lower()

    def test_fetch_url_connection_error(self):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError
        from requests.exceptions import ConnectionError

        with patch(
            "src.summarizer.ingestion.fetcher.requests.get",
            side_effect=ConnectionError("connection refused"),
        ):
            with pytest.raises(FetchError):
                fetch_url("https://unreachable.example.com/")

    def test_fetch_url_too_many_redirects(self):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError
        from requests.exceptions import TooManyRedirects

        with patch(
            "src.summarizer.ingestion.fetcher.requests.get",
            side_effect=TooManyRedirects("too many redirects"),
        ):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/redirect-loop")

        assert "redirect" in str(exc_info.value).lower()

    def test_fetch_url_unsupported_content_type(self, mock_response):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        response = mock_response(
            status_code=200,
            content=b"%PDF-1.4 binary content",
            content_type="application/pdf",
        )

        with patch("src.summarizer.ingestion.fetcher.requests.get", return_value=response):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/document.pdf")

        assert "content type" in str(exc_info.value).lower() or "unsupported" in str(exc_info.value).lower()

    def test_fetch_url_500_error(self, mock_response):
        from src.summarizer.ingestion.fetcher import fetch_url
        from src.summarizer.exceptions import FetchError

        response = mock_response(status_code=500, url="https://example.com/broken")

        with patch("src.summarizer.ingestion.fetcher.requests.get", return_value=response):
            with pytest.raises(FetchError) as exc_info:
                fetch_url("https://example.com/broken")

        assert "500" in str(exc_info.value)

    def test_fetch_url_returns_decoded_string(self, mock_response):
        from src.summarizer.ingestion.fetcher import fetch_url

        html_bytes = "<html><body><p>Héllo Wörld</p></body></html>".encode("utf-8")
        response = mock_response(content=html_bytes, encoding="utf-8")

        with patch("src.summarizer.ingestion.fetcher.requests.get", return_value=response):
            html, _ = fetch_url("https://example.com/")

        assert isinstance(html, str)
        assert "Héllo" in html


# ===========================================================================
# Tests: extractor
# ===========================================================================

class TestExtractor:
    def test_extract_from_sample_html(self, sample_html):
        from src.summarizer.ingestion.extractor import extract_article

        with patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=None), \
             patch("src.summarizer.ingestion.extractor._try_newspaper", return_value=None):
            article = extract_article(sample_html, url="https://example.com/renewable-energy")

        assert article.title == "The Rise of Renewable Energy: A Global Perspective"
        assert "renewable energy" in article.text.lower()
        assert article.word_count > 100
        assert article.url == "https://example.com/renewable-energy"

    def test_extract_article_tag(self, minimal_html):
        from src.summarizer.ingestion.extractor import extract_article

        with patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=None), \
             patch("src.summarizer.ingestion.extractor._try_newspaper", return_value=None):
            article = extract_article(minimal_html)

        assert "Test Article Heading" in article.text or "paragraph" in article.text.lower()
        # Nav and footer content should not dominate
        assert article.word_count > 10

    def test_extract_strips_scripts(self, minimal_html):
        from src.summarizer.ingestion.extractor import extract_article

        with patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=None), \
             patch("src.summarizer.ingestion.extractor._try_newspaper", return_value=None):
            article = extract_article(minimal_html)

        assert "console.log" not in article.text

    def test_extract_empty_html_raises(self):
        from src.summarizer.ingestion.extractor import extract_article
        from src.summarizer.exceptions import ParseError

        with pytest.raises(ParseError):
            extract_article("")

    def test_extract_whitespace_only_raises(self):
        from src.summarizer.ingestion.extractor import extract_article
        from src.summarizer.exceptions import ParseError

        with pytest.raises(ParseError):
            extract_article("   \n\t  ")

    def test_extract_title_from_og_meta(self):
        from src.summarizer.ingestion.extractor import extract_article

        html = """
        <html>
        <head>
            <meta property="og:title" content="OG Title Here">
            <title>Page Title</title>
        </head>
        <body>
        <article>
            <p>Long enough article content to pass word count minimum threshold for extraction.
            Adding more text here to ensure we are over the minimum word count requirement.
            This third sentence provides additional context and padding for the test.</p>
        </article>
        </body>
        </html>
        """
        with patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=None), \
             patch("src.summarizer.ingestion.extractor._try_newspaper", return_value=None):
            article = extract_article(html)

        assert article.title == "OG Title Here"

    def test_extract_title_fallback_to_title_tag(self):
        from src.summarizer.ingestion.extractor import extract_article

        html = """
        <html>
        <head><title>Fallback Title</title></head>
        <body>
        <article>
            <p>Long enough article content to pass word count minimum threshold for extraction.
            Adding more text here to ensure we are over the minimum word count requirement.
            This third sentence provides additional context and padding for the test.</p>
        </article>
        </body>
        </html>
        """
        with patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=None), \
             patch("src.summarizer.ingestion.extractor._try_newspaper", return_value=None):
            article = extract_article(html)

        assert article.title == "Fallback Title"

    def test_extract_uses_trafilatura_when_available(self):
        from src.summarizer.ingestion.extractor import extract_article

        html = """
        <html><head><title>Test</title></head>
        <body><article><p>placeholder</p></article></body>
        </html>
        """
        long_text = " ".join(["word"] * 100)

        with patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=long_text):
            article = extract_article(html)

        assert article.word_count == 100

    def test_extract_falls_back_to_newspaper(self):
        from src.summarizer.ingestion.extractor import extract_article

        html = """
        <html><head><title>Test</title></head>
        <body><article><p>placeholder</p></article></body>
        </html>
        """
        long_text = " ".join(["article"] * 60)

        with patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=None), \
             patch("src.summarizer.ingestion.extractor._try_newspaper", return_value=long_text):
            article = extract_article(html)

        assert article.word_count == 60

    def test_normalize_text_removes_zero_width(self):
        from src.summarizer.ingestion.extractor import normalize_text

        text = "Hello\u200bWorld\u00adTest"  # zero-width space, soft hyphen
        normalized = normalize_text(text)
        assert "\u200b" not in normalized
        assert "\u00ad" not in normalized

    def test_normalize_text_collapses_spaces(self):
        from src.summarizer.ingestion.extractor import normalize_text

        text = "Hello    World   this   is  a  test"
        normalized = normalize_text(text)
        assert "  " not in normalized

    def test_normalize_text_limits_blank_lines(self):
        from src.summarizer.ingestion.extractor import normalize_text

        text = "Line 1\n\n\n\n\n\nLine 2"
        normalized = normalize_text(text)
        lines = normalized.split("\n")
        # Count consecutive blank lines
        max_consecutive_blanks = 0
        current_blanks = 0
        for line in lines:
            if line == "":
                current_blanks += 1
                max_consecutive_blanks = max(max_consecutive_blanks, current_blanks)
            else:
                current_blanks = 0
        assert max_consecutive_blanks <= 2

    def test_normalize_text_empty_string(self):
        from src.summarizer.ingestion.extractor import normalize_text

        assert normalize_text("") == ""
        assert normalize_text(None) == ""


# ===========================================================================
# Tests: file_reader
# ===========================================================================

class TestFileReader:
    def test_read_txt_file(self):
        from src.summarizer.ingestion.file_reader import read_file

        content, file_type = read_file(SAMPLE_TXT_PATH)

        assert file_type == "txt"
        assert "renewable energy" in content.lower()
        assert len(content) > 100

    def test_read_html_file(self):
        from src.summarizer.ingestion.file_reader import read_file

        content, file_type = read_file(SAMPLE_HTML_PATH)

        assert file_type == "html"
        assert "<article>" in content
        assert "renewable energy" in content.lower()

    def test_read_file_not_found(self):
        from src.summarizer.ingestion.file_reader import read_file
        from src.summarizer.exceptions import FetchError

        with pytest.raises(FetchError) as exc_info:
            read_file("/nonexistent/path/to/article.txt")

        assert "not found" in str(exc_info.value).lower()

    def test_read_file_unsupported_extension(self, tmp_path):
        from src.summarizer.ingestion.file_reader import read_file
        from src.summarizer.exceptions import FetchError

        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 binary")

        with pytest.raises(FetchError) as exc_info:
            read_file(str(pdf_file))

        assert ".pdf" in str(exc_info.value)

    def test_read_empty_file(self, tmp_path):
        from src.summarizer.ingestion.file_reader import read_file
        from src.summarizer.exceptions import FetchError

        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        with pytest.raises(FetchError) as exc_info:
            read_file(str(empty_file))

        assert "empty" in str(exc_info.value).lower()

    def test_read_directory_raises(self, tmp_path):
        from src.summarizer.ingestion.file_reader import read_file
        from src.summarizer.exceptions import FetchError

        with pytest.raises(FetchError) as exc_info:
            read_file(str(tmp_path))

        assert "not a regular file" in str(exc_info.value).lower()

    def test_read_file_htm_extension(self, tmp_path):
        from src.summarizer.ingestion.file_reader import read_file

        htm_file = tmp_path / "article.htm"
        htm_file.write_text("<html><body><p>Hello</p></body></html>", encoding="utf-8")

        content, file_type = read_file(str(htm_file))

        assert file_type == "html"
        assert "Hello" in content

    def test_read_file_utf8_encoding(self, tmp_path):
        from src.summarizer.ingestion.file_reader import read_file

        txt_file = tmp_path / "unicode.txt"
        txt_file.write_text("Héllo Wörld — café naïve résumé", encoding="utf-8")

        content, _ = read_file(str(txt_file))

        assert "Héllo" in content
        assert "café" in content

    def test_read_file_latin1_encoding(self, tmp_path):
        from src.summarizer.ingestion.file_reader import read_file

        txt_file = tmp_path / "latin1.txt"
        txt_file.write_bytes("Héllo Wörld".encode("latin-1"))

        # Should not raise — fallback encoding should handle it
        content, _ = read_file(str(txt_file))
        assert len(content) > 0


# ===========================================================================
# Tests: fetch_article (integration-style with mocks)
# ===========================================================================

class TestFetchArticle:
    def test_fetch_article_from_url(self, sample_html, mock_response):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.models import SourceType

        response = mock_response(
            content=sample_html.encode("utf-8"),
            url="https://example.com/renewable-energy",
        )

        with patch("src.summarizer.ingestion.fetcher.requests.get", return_value=response), \
             patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=None), \
             patch("src.summarizer.ingestion.extractor._try_newspaper", return_value=None):
            article = fetch_article("https://example.com/renewable-energy")

        assert article.source_type == SourceType.URL
        assert article.url == "https://example.com/renewable-energy"
        assert article.word_count > 50
        assert article.title != ""

    def test_fetch_article_from_txt_file(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.models import SourceType

        article = fetch_article(SAMPLE_TXT_PATH)

        assert article.source_type == SourceType.FILE
        assert article.url is None
        assert article.word_count > 50
        assert "renewable" in article.text.lower()

    def test_fetch_article_from_html_file(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.models import SourceType

        with patch("src.summarizer.ingestion.extractor._try_trafilatura", return_value=None), \
             patch("src.summarizer.ingestion.extractor._try_newspaper", return_value=None):
            article = fetch_article(SAMPLE_HTML_PATH)

        assert article.source_type == SourceType.FILE
        assert article.url is None
        assert article.word_count > 50

    def test_fetch_article_nonexistent_file_raises(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.exceptions import FetchError

        with pytest.raises(FetchError):
            fetch_article("/nonexistent/article.txt")

    def test_fetch_article_url_fetch_error_propagates(self):
        from src.summarizer.ingestion import fetch_article
        from src.summarizer.exceptions import FetchError
        from requests.exceptions import ConnectionError

        with patch(
            "src.summarizer.ingestion.fetcher.requests.get",
            side_effect=ConnectionError("no route to host"),
        ):
            with pytest.raises(FetchError):
                fetch_article("https://unreachable.example.com/article")

    def test_fetch_article_title_set_for_txt(self):
        from src.summarizer.ingestion import fetch_article

        article = fetch_article(SAMPLE_TXT_PATH)

        # Title should be derived from the filename
        assert article.title != ""
        assert "sample" in article.title.lower() or "article" in article.title.lower()