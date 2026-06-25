"""Integration-style tests for the full summarize() pipeline using mocked LLM responses."""

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.summarizer.config import SummarizerConfig
from src.summarizer.exceptions import SummarizationError
from src.summarizer.llm.prompts import SummaryStyle
from src.summarizer.models import Article, Summary
from src.summarizer.summarize import summarize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(
    text: str = "This is a test article about AI.",
    title: str = "Test Article",
    url: str = "https://example.com/article",
) -> Article:
    return Article(text=text, title=title, url=url)


def _make_config(**kwargs) -> SummarizerConfig:
    defaults = dict(
        model="gpt-4o-mini",
        api_key="test-key",
        temperature=0.3,
        max_tokens=512,
        chunk_tokens=3000,
        overlap_tokens=200,
    )
    defaults.update(kwargs)
    return SummarizerConfig(**defaults)


def _openai_response(content: str, prompt_tokens: int = 50, completion_tokens: int = 30):
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=usage)


# ---------------------------------------------------------------------------
# Single-pass tests
# ---------------------------------------------------------------------------

class TestSummarizeSinglePass(unittest.TestCase):
    """Tests for articles that fit within the context window (single-pass)."""

    def _run_summarize(self, article, config, style=SummaryStyle.CONCISE, response_text="A concise summary."):
        mock_resp = _openai_response(response_text)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = mock_resp

            result = summarize(article, config=config, style=style)

        return result, mock_instance.chat.completions.create

    def test_returns_summary_dataclass(self):
        article = _make_article()
        config = _make_config()
        result, _ = self._run_summarize(article, config)
        assert isinstance(result, Summary)

    def test_summary_text_matches_response(self):
        article = _make_article()
        config = _make_config()
        result, _ = self._run_summarize(article, config, response_text="The AI revolution.")
        assert result.summary_text == "The AI revolution."

    def test_summary_contains_article_metadata(self):
        article = _make_article(title="My Article", url="https://example.com")
        config = _make_config()
        result, _ = self._run_summarize(article, config)
        assert result.article_title == "My Article"
        assert result.article_url == "https://example.com"

    def test_summary_records_model(self):
        article = _make_article()
        config = _make_config(model="gpt-4o-mini")
        result, _ = self._run_summarize(article, config)
        assert result.model == "gpt-4o-mini"

    def test_summary_records_style(self):
        article = _make_article()
        config = _make_config()
        result, _ = self._run_summarize(article, config, style=SummaryStyle.BULLET_POINTS)
        assert result.style == "bullet_points"

    def test_summary_records_token_usage(self):
        article = _make_article()
        config = _make_config()
        mock_resp = _openai_response("Summary.", prompt_tokens=40, completion_tokens=20)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = mock_resp
            result = summarize(article, config=config)

        assert result.prompt_tokens == 40
        assert result.completion_tokens == 20
        assert result.total_tokens == 60

    def test_strategy_is_single_pass(self):
        article = _make_article()
        config = _make_config()
        result, _ = self._run_summarize(article, config)
        assert result.strategy == "single-pass"

    def test_summary_has_created_at(self):
        article = _make_article()
        config = _make_config()
        result, _ = self._run_summarize(article, config)
        assert isinstance(result.created_at, datetime)

    def test_single_api_call_for_short_article(self):
        article = _make_article()
        config = _make_config()
        _, create_mock = self._run_summarize(article, config)
        assert create_mock.call_count == 1

    def test_all_styles_produce_summary(self):
        article = _make_article()
        config = _make_config()

        for style in SummaryStyle:
            mock_resp = _openai_response(f"Summary in {style.value} style.")
            with patch("openai.OpenAI") as MockOpenAI:
                mock_instance = MockOpenAI.return_value
                mock_instance.chat.completions.create.return_value = mock_resp
                result = summarize(article, config=config, style=style)
            assert result.style == style.value

    def test_empty_article_raises(self):
        article = _make_article(text="   ")
        config = _make_config()

        with patch("openai.OpenAI"):
            with pytest.raises(SummarizationError, match="empty"):
                summarize(article, config=config)

    def test_explicit_api_key_overrides_config(self):
        article = _make_article()
        config = _make_config(api_key="config-key")
        mock_resp = _openai_response("Summary.")

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = mock_resp
            result = summarize(article, config=config, api_key="override-key")

        # Should not raise; the explicit key should be used
        assert result.summary_text == "Summary."

    def test_untitled_article(self):
        article = Article(text="Some article text.", title=None, url=None)
        config = _make_config()
        mock_resp = _openai_response("Summary.")

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = mock_resp
            result = summarize(article, config=config)

        assert result.article_title == ""
        assert result.article_url == ""


# ---------------------------------------------------------------------------
# Map-reduce tests
# ---------------------------------------------------------------------------

class TestSummarizeMapReduce(unittest.TestCase):
    """Tests for articles that exceed the context window (map-reduce)."""

    def _make_long_article(self) -> Article:
        # Generate an article long enough to exceed the context window
        long_text = "This is a sentence about artificial intelligence. " * 10_000
        return Article(text=long_text, title="Long Article", url="https://example.com/long")

    def test_map_reduce_strategy_for_long_article(self):
        article = self._make_long_article()
        config = _make_config(chunk_tokens=500, overlap_tokens=50)

        call_responses = []

        def _create_side_effect(**kwargs):
            call_responses.append(kwargs)
            n = len(call_responses)
            return _openai_response(f"Summary {n}.", prompt_tokens=50, completion_tokens=20)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.side_effect = _create_side_effect
            result = summarize(article, config=config)

        assert result.strategy == "map-reduce"

    def test_map_reduce_makes_multiple_calls(self):
        article = self._make_long_article()
        config = _make_config(chunk_tokens=500, overlap_tokens=50)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = _openai_response(
                "Chunk summary.", prompt_tokens=50, completion_tokens=20
            )
            result = summarize(article, config=config)

        # Should have called API more than once (at least 2 chunks + merge)
        assert mock_instance.chat.completions.create.call_count > 1

    def test_map_reduce_accumulates_token_usage(self):
        article = self._make_long_article()
        config = _make_config(chunk_tokens=500, overlap_tokens=50)

        call_count = 0

        def _side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            return _openai_response("Summary.", prompt_tokens=100, completion_tokens=50)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.side_effect = _side_effect
            result = summarize(article, config=config)

        # Total tokens should be sum of all calls
        expected_total = call_count * 150  # 100 + 50 per call
        assert result.total_tokens == expected_total

    def test_map_reduce_returns_final_merged_summary(self):
        article = self._make_long_article()
        config = _make_config(chunk_tokens=500, overlap_tokens=50)

        responses = []

        def _side_effect(**kwargs):
            n = len(responses) + 1
            if n == 1:
                resp = _openai_response("Chunk 1 summary.")
            elif n > 1:
                resp = _openai_response("FINAL MERGED SUMMARY")
            responses.append(resp)
            return resp

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.side_effect = _side_effect
            result = summarize(article, config=config)

        assert "FINAL MERGED SUMMARY" in result.summary_text


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestSummarizeErrorHandling(unittest.TestCase):

    def test_api_error_raises_summarization_error(self):
        import openai as oai

        article = _make_article()
        config = _make_config()

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.side_effect = oai.AuthenticationError(
                "bad key",
                response=MagicMock(status_code=401, headers={}),
                body={},
            )

            with pytest.raises(SummarizationError):
                summarize(article, config=config)

    def test_missing_api_key_raises_summarization_error(self):
        import os

        article = _make_article()
        config = SummarizerConfig(model="gpt-4o-mini", api_key=None)

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises((SummarizationError, ValueError)):
                summarize(article, config=config)


if __name__ == "__main__":
    unittest.main()