"""Integration-style tests for the full summarize() pipeline using mocked LLM responses."""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from src.summarizer.config import Config
from src.summarizer.exceptions import SummarizerError
from src.summarizer.llm.client import SummarizerClient
from src.summarizer.models import Article, Summary
from src.summarizer.summarize import summarize, _direct_summarize, _chunked_summarize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_article(
    text: str = "This is a test article about climate change.",
    title: str = "Test Article",
) -> Article:
    return Article(text=text, title=title)


def make_config(**kwargs) -> Config:
    defaults = dict(
        openai_api_key="test-api-key",
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=1024,
        max_chunk_tokens=4000,
        overlap_tokens=200,
    )
    defaults.update(kwargs)
    return Config(**defaults)


def make_mock_client(responses=None, model="gpt-4o-mini") -> MagicMock:
    """Create a mock SummarizerClient."""
    client = MagicMock(spec=SummarizerClient)
    client.model = model
    if responses is None:
        responses = ["This is a generated summary."]
    client.complete.side_effect = responses if len(responses) > 1 else None
    if len(responses) == 1:
        client.complete.return_value = responses[0]
    return client


# ---------------------------------------------------------------------------
# Tests for summarize() — direct path
# ---------------------------------------------------------------------------


class TestSummarizeDirect:
    def test_returns_summary_dataclass(self):
        article = make_article()
        mock_client = make_mock_client(["This is a concise summary."])

        with patch("src.summarizer.summarize.fits_in_context", return_value=True):
            result = summarize(article, style="concise", client=mock_client)

        assert isinstance(result, Summary)

    def test_summary_text_matches_llm_response(self):
        article = make_article()
        expected = "Climate change is a pressing global issue."
        mock_client = make_mock_client([expected])

        with patch("src.summarizer.summarize.fits_in_context", return_value=True):
            result = summarize(article, client=mock_client)

        assert result.text == expected

    def test_summary_metadata_direct(self):
        article = make_article(title="My Article")
        mock_client = make_mock_client(["Summary text."])

        with patch("src.summarizer.summarize.fits_in_context", return_value=True):
            result = summarize(article, style="concise", client=mock_client)

        assert result.article_title == "My Article"
        assert result.style == "concise"
        assert result.model == "gpt-4o-mini"
        assert result.was_chunked is False
        assert result.chunk_count == 1

    def test_all_styles_work(self):
        for style in ["concise", "detailed", "bullet", "executive"]:
            article = make_article()
            mock_client = make_mock_client([f"Summary in {style} style."])

            with patch("src.summarizer.summarize.fits_in_context", return_value=True):
                result = summarize(article, style=style, client=mock_client)

            assert result.style == style
            assert f"Summary in {style} style." in result.text

    def test_client_complete_called_once_for_direct(self):
        article = make_article()
        mock_client = make_mock_client(["Summary."])

        with patch("src.summarizer.summarize.fits_in_context", return_value=True):
            summarize(article, client=mock_client)

        mock_client.complete.assert_called_once()

    def test_article_without_title(self):
        article = Article(text="Some article text with no title.")
        mock_client = make_mock_client(["Summary."])

        with patch("src.summarizer.summarize.fits_in_context", return_value=True):
            result = summarize(article, client=mock_client)

        assert result.article_title is None

    def test_creates_client_if_not_provided(self):
        """summarize() should create a SummarizerClient if none is provided."""
        article = make_article()
        config = make_config()

        with patch("src.summarizer.summarize.SummarizerClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.model = "gpt-4o-mini"
            mock_instance.complete.return_value = "Auto-created client summary."

            with patch("src.summarizer.summarize.fits_in_context", return_value=True):
                result = summarize(article, config=config)

        MockClient.assert_called_once_with(config=config)
        assert result.text == "Auto-created client summary."


# ---------------------------------------------------------------------------
# Tests for summarize() — chunked path
# ---------------------------------------------------------------------------


class TestSummarizeChunked:
    def test_long_article_uses_chunked_path(self):
        article = make_article(text="word " * 10000)
        mock_client = make_mock_client([
            "Chunk 1 summary.",
            "Chunk 2 summary.",
            "Final merged summary.",
        ])

        with patch("src.summarizer.summarize.fits_in_context", return_value=False):
            with patch("src.summarizer.summarize.TextChunker") as MockChunker:
                mock_chunker_instance = MockChunker.return_value
                mock_chunker_instance.split.return_value = ["chunk1 text", "chunk2 text"]

                with patch("src.summarizer.summarize.MapReduceSummarizer") as MockMR:
                    mock_mr_instance = MockMR.return_value
                    mock_mr_instance.summarize.return_value = "Final merged summary."

                    result = summarize(article, client=mock_client)

        assert result.was_chunked is True
        mock_mr_instance.summarize.assert_called_once()

    def test_chunked_metadata(self):
        article = make_article(text="word " * 10000, title="Long Article")
        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.model = "gpt-4o-mini"

        with patch("src.summarizer.summarize.fits_in_context", return_value=False):
            with patch("src.summarizer.summarize.TextChunker") as MockChunker:
                mock_chunker_instance = MockChunker.return_value
                mock_chunker_instance.split.return_value = ["c1", "c2", "c3"]

                with patch("src.summarizer.summarize.MapReduceSummarizer") as MockMR:
                    mock_mr_instance = MockMR.return_value
                    mock_mr_instance.summarize.return_value = "Merged summary."

                    result = summarize(article, client=mock_client)

        assert result.was_chunked is True
        assert result.chunk_count == 3
        assert result.article_title == "Long Article"

    def test_chunker_initialized_with_config_params(self):
        article = make_article()
        config = make_config(max_chunk_tokens=2000, overlap_tokens=100)
        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.model = "gpt-4o-mini"

        with patch("src.summarizer.summarize.fits_in_context", return_value=False):
            with patch("src.summarizer.summarize.TextChunker") as MockChunker:
                mock_chunker_instance = MockChunker.return_value
                mock_chunker_instance.split.return_value = ["chunk1"]

                with patch("src.summarizer.summarize.MapReduceSummarizer") as MockMR:
                    mock_mr_instance = MockMR.return_value
                    mock_mr_instance.summarize.return_value = "Summary."

                    summarize(article, config=config, client=mock_client)

        MockChunker.assert_called_once_with(
            model="gpt-4o-mini",
            max_chunk_tokens=2000,
            overlap_tokens=100,
        )


# ---------------------------------------------------------------------------
# Tests for error handling
# ---------------------------------------------------------------------------


class TestSummarizeErrorHandling:
    def test_api_error_raises_summarizer_error(self):
        import openai
        article = make_article()
        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.model = "gpt-4o-mini"
        mock_client.complete.side_effect = openai.OpenAIError("API error")

        with patch("src.summarizer.summarize.fits_in_context", return_value=True):
            with pytest.raises(SummarizerError):
                summarize(article, client=mock_client)

    def test_summarizer_error_propagates_directly(self):
        article = make_article()
        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.model = "gpt-4o-mini"
        mock_client.complete.side_effect = SummarizerError("Already a SummarizerError")

        with patch("src.summarizer.summarize.fits_in_context", return_value=True):
            with pytest.raises(SummarizerError, match="Already a SummarizerError"):
                summarize(article, client=mock_client)

    def test_invalid_style_raises_value_error(self):
        article = make_article()
        mock_client = make_mock_client()

        with pytest.raises(ValueError, match="Unknown style"):
            summarize(article, style="invalid_style", client=mock_client)


# ---------------------------------------------------------------------------
# Tests for _direct_summarize and _chunked_summarize helpers
# ---------------------------------------------------------------------------


class TestDirectSummarizeHelper:
    def test_returns_tuple(self):
        article = make_article()
        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.complete.return_value = "Direct summary."
        prompt_builder = MagicMock()
        prompt_builder.build_direct_messages.return_value = [{"role": "user", "content": "test"}]

        text, was_chunked, chunk_count = _direct_summarize(article, mock_client, prompt_builder)

        assert text == "Direct summary."
        assert was_chunked is False
        assert chunk_count == 1

    def test_calls_build_direct_messages(self):
        article = make_article(text="Article text", title="Title")
        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.complete.return_value = "Summary."
        prompt_builder = MagicMock()
        prompt_builder.build_direct_messages.return_value = [{"role": "user", "content": "msg"}]

        _direct_summarize(article, mock_client, prompt_builder)

        prompt_builder.build_direct_messages.assert_called_once_with(
            article_text="Article text",
            title="Title",
        )


class TestChunkedSummarizeHelper:
    def test_returns_was_chunked_true(self):
        article = make_article(text="word " * 5000)
        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.model = "gpt-4o-mini"
        prompt_builder = MagicMock()
        config = make_config()

        with patch("src.summarizer.summarize.TextChunker") as MockChunker:
            mock_chunker_instance = MockChunker.return_value
            mock_chunker_instance.split.return_value = ["c1", "c2"]

            with patch("src.summarizer.summarize.MapReduceSummarizer") as MockMR:
                mock_mr_instance = MockMR.return_value
                mock_mr_instance.summarize.return_value = "Chunked summary."

                text, was_chunked, chunk_count = _chunked_summarize(
                    article, mock_client, prompt_builder, config
                )

        assert was_chunked is True
        assert chunk_count == 2
        assert text == "Chunked summary."


# ---------------------------------------------------------------------------
# Integration smoke test (no real API calls)
# ---------------------------------------------------------------------------


class TestSummarizePipelineSmoke:
    """End-to-end smoke tests that exercise the full call chain with mocks."""

    def test_short_article_direct_path_full_chain(self):
        """Verify the full direct path without patching internal functions."""
        article = Article(
            text="OpenAI has released GPT-5, a new language model with improved reasoning.",
            title="OpenAI Releases GPT-5",
        )
        config = make_config()

        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = "GPT-5 is OpenAI's latest model."
        mock_openai_response.usage.prompt_tokens = 50
        mock_openai_response.usage.completion_tokens = 15
        mock_openai_response.usage.total_tokens = 65

        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_openai_instance = MockOpenAI.return_value
            mock_openai_instance.chat.completions.create.return_value = mock_openai_response

            result = summarize(article, style="concise", config=config)

        assert isinstance(result, Summary)
        assert result.text == "GPT-5 is OpenAI's latest model."
        assert result.was_chunked is False
        assert result.chunk_count == 1
        assert result.style == "concise"
        assert result.article_title == "OpenAI Releases GPT-5"