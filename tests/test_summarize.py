"""Integration-style tests for the full summarize() pipeline.

Uses mocked LLM responses to test orchestration logic without hitting
the real OpenAI API.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.summarizer.config import Config
from src.summarizer.llm.prompts import SummaryStyle
from src.summarizer.models import Article, Summary
from src.summarizer.summarize import summarize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config() -> Config:
    return Config(
        openai_api_key="test-key",
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=256,
    )


def _make_openai_response(
    content: str = "A great summary.",
    prompt_tokens: int = 80,
    completion_tokens: int = 20,
):
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = prompt_tokens + completion_tokens

    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


def _make_article(
    title: str = "Test Article",
    text: str = "This is the article body text.",
    url: str = "https://example.com/article",
) -> Article:
    return Article(url=url, title=title, text=text)


# ---------------------------------------------------------------------------
# Basic pipeline tests
# ---------------------------------------------------------------------------

class TestSummarizePipeline:
    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_returns_summary_dataclass(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response(
            "This is the summary."
        )

        article = _make_article()
        result = summarize(article, config=_make_config())

        assert isinstance(result, Summary)

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_contains_expected_text(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response(
            "Expected summary text."
        )

        article = _make_article(text="Article body.")
        result = summarize(article, config=_make_config())

        assert result.summary == "Expected summary text."

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_title_matches_article_title(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response()

        article = _make_article(title="My Special Title")
        result = summarize(article, config=_make_config())

        assert result.title == "My Special Title"

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_model_matches_config(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response()

        config = _make_config()
        config.model = "gpt-4o-mini"
        article = _make_article()
        result = summarize(article, config=config)

        assert result.model == "gpt-4o-mini"

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_token_counts_are_populated(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response(
            "Summary.", prompt_tokens=120, completion_tokens=30
        )

        article = _make_article()
        result = summarize(article, config=_make_config())

        assert result.prompt_tokens == 120
        assert result.completion_tokens == 30
        assert result.total_tokens == 150

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_estimated_cost_is_calculated(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response(
            "Summary.", prompt_tokens=1000, completion_tokens=1000
        )

        article = _make_article()
        result = summarize(article, config=_make_config())

        assert result.estimated_cost > 0.0


# ---------------------------------------------------------------------------
# Empty / edge case articles
# ---------------------------------------------------------------------------

class TestSummarizeEdgeCases:
    def test_empty_article_text_returns_empty_summary(self):
        article = _make_article(text="")
        result = summarize(article, config=_make_config())

        assert result.summary == ""
        assert result.total_tokens == 0
        assert result.estimated_cost == 0.0

    def test_whitespace_only_article_returns_empty_summary(self):
        article = _make_article(text="   \n\t  ")
        result = summarize(article, config=_make_config())

        assert result.summary == ""

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_article_with_no_title(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response("s")

        article = Article(url="https://example.com", title="", text="Some text.")
        result = summarize(article, config=_make_config())

        assert result.title == ""


# ---------------------------------------------------------------------------
# Style parameterization
# ---------------------------------------------------------------------------

class TestSummarizeStyles:
    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    @pytest.mark.parametrize("style", list(SummaryStyle))
    def test_all_styles_complete_successfully(self, mock_openai_cls, mock_fits, style):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response(
            f"Summary in {style} style."
        )

        article = _make_article()
        result = summarize(article, config=_make_config(), style=style)

        assert isinstance(result, Summary)
        assert result.summary != ""


# ---------------------------------------------------------------------------
# Chunked pipeline integration
# ---------------------------------------------------------------------------

class TestSummarizeChunkedPipeline:
    @patch("src.summarizer.llm.client.fits_in_context", return_value=False)
    @patch("src.summarizer.llm.chunker.split_into_chunks")
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_long_article_uses_chunked_strategy(
        self, mock_openai_cls, mock_split, mock_fits
    ):
        from src.summarizer.llm.chunker import TextChunk

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_split.return_value = [
            TextChunk(text="part one", index=1, total=2, token_count=5),
            TextChunk(text="part two", index=2, total=2, token_count=5),
        ]

        mock_client.chat.completions.create.side_effect = [
            _make_openai_response("Chunk 1 summary."),
            _make_openai_response("Chunk 2 summary."),
            _make_openai_response("Final unified summary."),
        ]

        article = _make_article(text="a " * 10000)
        result = summarize(article, config=_make_config())

        assert result.summary == "Final unified summary."
        # 2 map + 1 reduce
        assert mock_client.chat.completions.create.call_count == 3

    @patch("src.summarizer.llm.client.fits_in_context", return_value=False)
    @patch("src.summarizer.llm.chunker.split_into_chunks")
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_chunked_summary_has_aggregated_token_usage(
        self, mock_openai_cls, mock_split, mock_fits
    ):
        from src.summarizer.llm.chunker import TextChunk

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_split.return_value = [
            TextChunk(text="a", index=1, total=1, token_count=1),
        ]

        mock_client.chat.completions.create.side_effect = [
            _make_openai_response("Partial.", prompt_tokens=40, completion_tokens=10),
            _make_openai_response("Final.", prompt_tokens=20, completion_tokens=15),
        ]

        article = _make_article(text="a " * 5000)
        result = summarize(article, config=_make_config())

        assert result.prompt_tokens == 60
        assert result.completion_tokens == 25
        assert result.total_tokens == 85