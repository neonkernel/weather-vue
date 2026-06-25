"""Integration-style tests for the full summarize() pipeline with mocked LLM."""

from __future__ import annotations

import sys
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from summarizer.summarize import summarize
from summarizer.models import Article, Summary
from summarizer.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content: str, prompt_tokens: int = 50, completion_tokens: int = 80):
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=usage)


def _article(content: str = "This is a test article about AI.", url: str = "https://example.com/article") -> Article:
    return Article(url=url, title="Test Article", content=content)


# ---------------------------------------------------------------------------
# Basic summarization
# ---------------------------------------------------------------------------

class TestSummarizePipeline:
    def _run(self, content: str = "Short article.", style="concise", **kwargs) -> Summary:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("Mocked summary text.")
        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            article = _article(content)
            result = summarize(article, style=style, **kwargs)
        return result

    def test_returns_summary_dataclass(self):
        result = self._run()
        assert isinstance(result, Summary)

    def test_summary_text_populated(self):
        result = self._run()
        assert result.summary == "Mocked summary text."

    def test_summary_url_matches_article(self):
        result = self._run()
        assert result.url == "https://example.com/article"

    def test_summary_title_matches_article(self):
        result = self._run()
        assert result.title == "Test Article"

    def test_summary_model_set(self):
        result = self._run(model="gpt-4o-mini")
        assert result.model == "gpt-4o-mini"

    def test_summary_style_set(self):
        result = self._run(style="bullet")
        assert result.style == "bullet"

    def test_token_counts_populated(self):
        result = self._run()
        assert result.prompt_tokens == 50
        assert result.completion_tokens == 80

    def test_total_tokens_property(self):
        result = self._run()
        assert result.total_tokens == 130

    def test_created_at_is_datetime(self):
        result = self._run()
        assert isinstance(result.created_at, datetime)

    def test_raises_on_empty_content(self):
        with pytest.raises(ValueError, match="no content"):
            mock_openai = MagicMock()
            with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
                summarize(_article(content=""))

    def test_raises_on_whitespace_content(self):
        with pytest.raises(ValueError, match="no content"):
            mock_openai = MagicMock()
            with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
                summarize(_article(content="   \n\t  "))


# ---------------------------------------------------------------------------
# Style variations
# ---------------------------------------------------------------------------

class TestSummarizeStyles:
    def _mock_and_run(self, style: str) -> tuple[Summary, MagicMock]:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response(f"{style} summary")
        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            result = summarize(_article(), style=style)
        return result, mock_openai

    def test_concise_style(self):
        result, _ = self._mock_and_run("concise")
        assert result.style == "concise"

    def test_detailed_style(self):
        result, _ = self._mock_and_run("detailed")
        assert result.style == "detailed"

    def test_bullet_style(self):
        result, _ = self._mock_and_run("bullet")
        assert result.style == "bullet"


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------

class TestSummarizeWithConfig:
    def test_config_model_used(self):
        cfg = Config(model="gpt-4o", openai_api_key="test-key")
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("ok")
        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            result = summarize(_article(), config=cfg)
        assert result.model == "gpt-4o"

    def test_model_override_takes_priority(self):
        cfg = Config(model="gpt-4o")
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("ok")
        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            result = summarize(_article(), config=cfg, model="gpt-4o-mini")
        assert result.model == "gpt-4o-mini"

    def test_no_config_uses_defaults(self):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("ok")
        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            result = summarize(_article())
        assert result.model == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Chunked (map-reduce) path
# ---------------------------------------------------------------------------

class TestSummarizeChunked:
    def test_long_article_uses_map_reduce(self):
        long_content = "word " * 200_000
        article = _article(content=long_content)

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("partial")

        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            with patch("summarizer.llm.client.map_reduce_summarize", return_value="Chunked final summary.") as mock_mr:
                with patch("summarizer.llm.client.fits_in_context", return_value=False):
                    result = summarize(article)

        mock_mr.assert_called_once()
        assert result.summary == "Chunked final summary."

    def test_short_article_does_not_use_map_reduce(self):
        article = _article(content="A short article.")

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("Direct summary.")

        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            with patch("summarizer.llm.client.map_reduce_summarize") as mock_mr:
                result = summarize(article)

        mock_mr.assert_not_called()
        assert result.summary == "Direct summary."


# ---------------------------------------------------------------------------
# Extra instructions
# ---------------------------------------------------------------------------

class TestExtraInstructions:
    def test_extra_instructions_forwarded(self):
        article = _article()
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("Summary with focus.")

        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            result = summarize(article, extra_instructions="Focus on economic impact.")

        # Verify the API was called
        assert mock_openai.chat.completions.create.called
        # Check that the system message contains the extra instructions
        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][0] if call_args[0] else []
        system_messages = [m for m in messages if m.get("role") == "system"]
        assert any("Focus on economic impact." in m["content"] for m in system_messages)