"""Integration-style tests for the full summarize() pipeline."""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from summarizer.config import Config
from summarizer.exceptions import SummarizerError
from summarizer.llm.client import SummarizerClient
from summarizer.llm.prompts import SummaryStyle
from summarizer.models import Article, Summary
from summarizer.summarize import summarize


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def short_article() -> Article:
    return Article(
        content="Scientists have discovered a new species of deep-sea fish "
                "off the coast of New Zealand. The fish, named Bathypelagicus "
                "novus, lives at depths of over 3,000 meters.",
        title="New Deep-Sea Fish Discovered",
        url="https://example.com/fish",
    )


@pytest.fixture
def long_article() -> Article:
    paragraph = (
        "The global economy continues to face significant challenges in the "
        "wake of unprecedented disruptions. Analysts from major financial "
        "institutions warn that inflation, supply chain bottlenecks, and "
        "geopolitical tensions are creating a perfect storm for markets. "
        "Central banks around the world are raising interest rates in an "
        "attempt to tame inflation, but critics argue these measures risk "
        "triggering a recession. "
    )
    return Article(
        content=paragraph * 50,  # ~350 words repeated
        title="Global Economic Outlook",
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """A pre-configured mock SummarizerClient."""
    client = MagicMock(spec=SummarizerClient)
    client.complete.return_value = ("A concise summary.", 100, 50)
    return client


@pytest.fixture
def config() -> Config:
    return Config(
        openai_api_key="test-key",
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=512,
        max_retries=3,
    )


# ---------------------------------------------------------------------------
# Basic summarize() tests
# ---------------------------------------------------------------------------


class TestSummarize:
    def test_returns_summary_object(self, short_article, mock_client, config):
        result = summarize(short_article, config=config, client=mock_client)
        assert isinstance(result, Summary)

    def test_summary_has_correct_title(self, short_article, mock_client, config):
        result = summarize(short_article, config=config, client=mock_client)
        assert result.article_title == "New Deep-Sea Fish Discovered"

    def test_summary_text_is_non_empty(self, short_article, mock_client, config):
        result = summarize(short_article, config=config, client=mock_client)
        assert len(result.summary) > 0

    def test_summary_contains_llm_response(self, short_article, mock_client, config):
        mock_client.complete.return_value = ("Deep sea fish found.", 50, 20)
        result = summarize(short_article, config=config, client=mock_client)
        assert result.summary == "Deep sea fish found."

    def test_summary_has_model_name(self, short_article, mock_client, config):
        result = summarize(short_article, config=config, client=mock_client)
        assert result.model == "gpt-4o-mini"

    def test_summary_has_token_counts(self, short_article, config):
        client = MagicMock(spec=SummarizerClient)
        client.complete.return_value = ("Summary text.", 100, 50)
        result = summarize(short_article, config=config, client=client)
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 50
        assert result.total_tokens == 150

    def test_summary_strategy_direct_for_short_article(
        self, short_article, mock_client, config
    ):
        result = summarize(short_article, config=config, client=mock_client)
        assert result.strategy == "direct"

    def test_article_without_title_uses_untitled(self, mock_client, config):
        article = Article(content="Some content here.")
        result = summarize(article, config=config, client=mock_client)
        assert result.article_title == "Untitled"

    def test_summary_text_is_stripped(self, short_article, config):
        client = MagicMock(spec=SummarizerClient)
        client.complete.return_value = ("  Summary with spaces.  ", 50, 20)
        result = summarize(short_article, config=config, client=client)
        assert result.summary == "Summary with spaces."


# ---------------------------------------------------------------------------
# Strategy selection tests
# ---------------------------------------------------------------------------


class TestStrategySelection:
    def test_direct_strategy_when_content_fits(self, short_article, mock_client, config):
        with patch("summarizer.summarize.fits_in_context", return_value=True):
            result = summarize(short_article, config=config, client=mock_client)
        assert result.strategy == "direct"

    def test_map_reduce_strategy_when_content_too_long(
        self, long_article, config
    ):
        mock_client = MagicMock(spec=SummarizerClient)
        # map calls + reduce call
        mock_client.complete.side_effect = [
            ("Chunk summary 1.", 100, 40),
            ("Chunk summary 2.", 110, 45),
            ("Final summary.", 200, 80),
        ]

        with patch("summarizer.summarize.fits_in_context", return_value=False), \
             patch("summarizer.summarize.map_reduce_summarize") as mock_mr:
            mock_mr.return_value = ("Map-reduce summary.", 500, 150)
            result = summarize(long_article, config=config, client=mock_client)

        assert result.strategy == "map_reduce"
        assert result.summary == "Map-reduce summary."

    def test_map_reduce_called_with_correct_args(self, long_article, config):
        mock_client = MagicMock(spec=SummarizerClient)

        with patch("summarizer.summarize.fits_in_context", return_value=False), \
             patch("summarizer.summarize.map_reduce_summarize") as mock_mr:
            mock_mr.return_value = ("Summary.", 100, 50)
            summarize(long_article, config=config, client=mock_client)

        mock_mr.assert_called_once()
        call_kwargs = mock_mr.call_args.kwargs
        assert call_kwargs["text"] == long_article.content
        assert call_kwargs["title"] == long_article.title
        assert call_kwargs["client"] == mock_client
        assert call_kwargs["model"] == config.model


# ---------------------------------------------------------------------------
# Style tests
# ---------------------------------------------------------------------------


class TestSummarizeStyles:
    @pytest.mark.parametrize("style", list(SummaryStyle))
    def test_all_styles_produce_summary(self, short_article, config, style):
        client = MagicMock(spec=SummarizerClient)
        client.complete.return_value = ("Summary.", 50, 20)
        result = summarize(short_article, config=config, style=style, client=client)
        assert isinstance(result, Summary)

    def test_style_affects_prompt(self, short_article, config):
        """Different styles should result in different prompts being sent."""
        captured_messages = []

        def capture_messages(messages):
            captured_messages.append(messages)
            return "Summary.", 50, 20

        client = MagicMock(spec=SummarizerClient)
        client.complete.side_effect = capture_messages

        summarize(short_article, config=config, style=SummaryStyle.CONCISE, client=client)
        client.reset_mock()
        client.complete.side_effect = capture_messages

        summarize(short_article, config=config, style=SummaryStyle.DETAILED, client=client)

        assert len(captured_messages) == 2
        # The system prompts should differ between styles
        concise_system = captured_messages[0][0]["content"]
        detailed_system = captured_messages[1][0]["content"]
        assert concise_system != detailed_system


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestSummarizeErrorHandling:
    def test_raises_summarizer_error_on_api_failure(self, short_article, config):
        client = MagicMock(spec=SummarizerClient)
        client.complete.side_effect = RuntimeError("API is down")

        with pytest.raises(SummarizerError, match="Failed to summarize article"):
            summarize(short_article, config=config, client=client)

    def test_original_exception_is_chained(self, short_article, config):
        client = MagicMock(spec=SummarizerClient)
        original_error = ValueError("Something went wrong")
        client.complete.side_effect = original_error

        with pytest.raises(SummarizerError) as exc_info:
            summarize(short_article, config=config, client=client)

        assert exc_info.value.__cause__ is original_error

    def test_empty_article_content_raises_value_error(self):
        with pytest.raises(ValueError, match="content cannot be empty"):
            Article(content="")


# ---------------------------------------------------------------------------
# Client creation tests
# ---------------------------------------------------------------------------


class TestClientCreation:
    def test_client_created_from_config_when_not_provided(
        self, short_article, config
    ):
        with patch("summarizer.summarize.SummarizerClient") as MockClient:
            mock_instance = MagicMock(spec=SummarizerClient)
            mock_instance.complete.return_value = ("Summary.", 50, 20)
            MockClient.return_value = mock_instance

            result = summarize(short_article, config=config)

        MockClient.assert_called_once_with(
            api_key=config.openai_api_key,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            max_retries=config.max_retries,
            base_url=None,
        )

    def test_provided_client_is_used_directly(self, short_article, config):
        """When a client is passed in, no new client should be created."""
        custom_client = MagicMock(spec=SummarizerClient)
        custom_client.complete.return_value = ("Custom summary.", 50, 20)

        with patch("summarizer.summarize.SummarizerClient") as MockClient:
            result = summarize(short_article, config=config, client=custom_client)

        MockClient.assert_not_called()
        assert result.summary == "Custom summary."


# ---------------------------------------------------------------------------
# Summary dataclass tests
# ---------------------------------------------------------------------------


class TestSummaryDataclass:
    def test_total_tokens_property(self):
        summary = Summary(
            article_title="Test",
            summary="A summary.",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert summary.total_tokens == 150

    def test_default_strategy_is_direct(self):
        summary = Summary(
            article_title="Test",
            summary="A summary.",
            model="gpt-4o-mini",
        )
        assert summary.strategy == "direct"

    def test_summary_str_representation(self):
        summary = Summary(
            article_title="My Article",
            summary="Short summary.",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=5,
        )
        repr_str = repr(summary)
        assert "My Article" in repr_str