"""Tests for SummarizerClient with mocked OpenAI responses.

Covers:
- Direct summarization (article fits in context)
- Chunked (map-reduce) summarization
- Retry behavior on transient errors
- Prompt construction
- Token usage logging
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass

import openai

from src.summarizer.config import Config
from src.summarizer.llm.client import SummarizerClient
from src.summarizer.llm.prompts import PromptBuilder, SummaryStyle, Message
from src.summarizer.models import Summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(model: str = "gpt-4o-mini") -> Config:
    return Config(
        openai_api_key="test-key",
        model=model,
        temperature=0.3,
        max_tokens=256,
    )


def _make_openai_response(content: str, prompt_tokens: int = 50, completion_tokens: int = 30):
    """Build a minimal mock that looks like an openai ChatCompletion response."""
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


# ---------------------------------------------------------------------------
# PromptBuilder tests
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def test_build_direct_messages_returns_two_messages(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        msgs = builder.build_direct_messages("Some article text here.")
        assert len(msgs) == 2
        assert msgs[0].role == "system"
        assert msgs[1].role == "user"

    def test_build_direct_messages_contains_article_text(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        article_text = "Breaking news: everything is fine."
        msgs = builder.build_direct_messages(article_text)
        assert article_text in msgs[1].content

    def test_build_chunk_messages(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        msgs = builder.build_chunk_messages("chunk text", chunk_index=1, total_chunks=3)
        assert len(msgs) == 2
        assert "1 of 3" in msgs[1].content
        assert "chunk text" in msgs[1].content

    def test_build_reduce_messages(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        partials = ["Summary A.", "Summary B."]
        msgs = builder.build_reduce_messages(partials)
        assert len(msgs) == 2
        assert "Summary A." in msgs[1].content
        assert "Summary B." in msgs[1].content

    def test_message_to_dict(self):
        msg = Message(role="user", content="hello")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "hello"}

    @pytest.mark.parametrize("style", list(SummaryStyle))
    def test_all_styles_produce_messages(self, style):
        builder = PromptBuilder(style=style)
        msgs = builder.build_direct_messages("text")
        assert len(msgs) == 2


# ---------------------------------------------------------------------------
# SummarizerClient — direct summarization
# ---------------------------------------------------------------------------

class TestSummarizerClientDirect:
    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_direct_summarize_returns_summary(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response(
            "This is a summary.", prompt_tokens=100, completion_tokens=20
        )

        config = _make_config()
        client = SummarizerClient(config=config)
        result = client.summarize("Long article text here.", title="Test Article")

        assert isinstance(result, Summary)
        assert result.summary == "This is a summary."
        assert result.title == "Test Article"
        assert result.model == "gpt-4o-mini"
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 20
        assert result.total_tokens == 120

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_direct_summarize_calls_api_once(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response("Summary.")

        config = _make_config()
        client = SummarizerClient(config=config)
        client.summarize("Article text.", title="T")

        assert mock_client.chat.completions.create.call_count == 1

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_estimated_cost_is_non_negative(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response(
            "Summary.", prompt_tokens=200, completion_tokens=50
        )

        config = _make_config()
        client = SummarizerClient(config=config)
        result = client.summarize("text")

        assert result.estimated_cost >= 0.0

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_temperature_passed_to_api(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response("s")

        config = _make_config()
        config.temperature = 0.7
        client = SummarizerClient(config=config)
        client.summarize("text")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_max_tokens_passed_to_api(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_openai_response("s")

        config = _make_config()
        config.max_tokens = 512
        client = SummarizerClient(config=config)
        client.summarize("text")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["max_tokens"] == 512


# ---------------------------------------------------------------------------
# SummarizerClient — chunked (map-reduce) summarization
# ---------------------------------------------------------------------------

class TestSummarizerClientChunked:
    @patch("src.summarizer.llm.client.fits_in_context", return_value=False)
    @patch("src.summarizer.llm.chunker.split_into_chunks")
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_chunked_summarize_calls_api_for_each_chunk_plus_reduce(
        self, mock_openai_cls, mock_split, mock_fits
    ):
        from src.summarizer.llm.chunker import TextChunk

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Three chunks
        mock_split.return_value = [
            TextChunk(text="chunk1", index=1, total=3, token_count=10),
            TextChunk(text="chunk2", index=2, total=3, token_count=10),
            TextChunk(text="chunk3", index=3, total=3, token_count=10),
        ]

        responses = [
            _make_openai_response("Partial summary 1."),
            _make_openai_response("Partial summary 2."),
            _make_openai_response("Partial summary 3."),
            _make_openai_response("Final combined summary."),
        ]
        mock_client.chat.completions.create.side_effect = responses

        config = _make_config()
        client = SummarizerClient(config=config)
        result = client.summarize("very long article text")

        # 3 map calls + 1 reduce call
        assert mock_client.chat.completions.create.call_count == 4
        assert result.summary == "Final combined summary."

    @patch("src.summarizer.llm.client.fits_in_context", return_value=False)
    @patch("src.summarizer.llm.chunker.split_into_chunks")
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_chunked_summarize_aggregates_token_usage(
        self, mock_openai_cls, mock_split, mock_fits
    ):
        from src.summarizer.llm.chunker import TextChunk

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_split.return_value = [
            TextChunk(text="chunk1", index=1, total=2, token_count=10),
            TextChunk(text="chunk2", index=2, total=2, token_count=10),
        ]

        responses = [
            _make_openai_response("Partial 1.", prompt_tokens=50, completion_tokens=10),
            _make_openai_response("Partial 2.", prompt_tokens=50, completion_tokens=10),
            _make_openai_response("Final.", prompt_tokens=30, completion_tokens=20),
        ]
        mock_client.chat.completions.create.side_effect = responses

        config = _make_config()
        client = SummarizerClient(config=config)
        result = client.summarize("long text")

        expected_prompt = 50 + 50 + 30
        expected_completion = 10 + 10 + 20
        assert result.prompt_tokens == expected_prompt
        assert result.completion_tokens == expected_completion
        assert result.total_tokens == expected_prompt + expected_completion


# ---------------------------------------------------------------------------
# Retry behavior
# ---------------------------------------------------------------------------

class TestRetryBehavior:
    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_retries_on_rate_limit_error(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Fail twice, succeed on third attempt
        mock_client.chat.completions.create.side_effect = [
            openai.RateLimitError("rate limit", response=MagicMock(), body={}),
            openai.RateLimitError("rate limit", response=MagicMock(), body={}),
            _make_openai_response("Success after retries."),
        ]

        config = _make_config()
        client = SummarizerClient(config=config)

        # Patch tenacity sleep to speed up test
        with patch("tenacity.nap.time.sleep"):
            result = client.summarize("some text")

        assert result.summary == "Success after retries."
        assert mock_client.chat.completions.create.call_count == 3

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_raises_after_max_retries(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            "rate limit", response=MagicMock(), body={}
        )

        config = _make_config()
        client = SummarizerClient(config=config)

        with patch("tenacity.nap.time.sleep"):
            with pytest.raises(openai.RateLimitError):
                client.summarize("some text")

        assert mock_client.chat.completions.create.call_count == 3

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_retries_on_api_connection_error(self, mock_openai_cls, mock_fits):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_client.chat.completions.create.side_effect = [
            openai.APIConnectionError(request=MagicMock()),
            _make_openai_response("Recovered."),
        ]

        config = _make_config()
        client = SummarizerClient(config=config)

        with patch("tenacity.nap.time.sleep"):
            result = client.summarize("text")

        assert result.summary == "Recovered."

    @patch("src.summarizer.llm.client.fits_in_context", return_value=True)
    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_does_not_retry_on_auth_error(self, mock_openai_cls, mock_fits):
        """AuthenticationError is not transient; should not be retried."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            "bad key", response=MagicMock(), body={}
        )

        config = _make_config()
        client = SummarizerClient(config=config)

        with pytest.raises(openai.AuthenticationError):
            client.summarize("text")

        # Should only be called once — no retries for auth errors
        assert mock_client.chat.completions.create.call_count == 1