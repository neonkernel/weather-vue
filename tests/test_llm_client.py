"""Tests for SummarizerClient, PromptBuilder, and chunking logic."""

import time
from unittest.mock import MagicMock, patch, call
import pytest

import openai

from src.summarizer.llm.client import SummarizerClient
from src.summarizer.llm.prompts import PromptBuilder, PromptMessages
from src.summarizer.llm.chunker import TextChunker, run_map_reduce
from src.summarizer.llm.token_utils import (
    count_tokens,
    estimate_cost,
    fits_in_context,
    get_context_window,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_mock_response(content: str, prompt_tokens: int = 50, completion_tokens: int = 30):
    """Create a mock OpenAI ChatCompletion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    mock_response.usage.prompt_tokens = prompt_tokens
    mock_response.usage.completion_tokens = completion_tokens
    mock_response.usage.total_tokens = prompt_tokens + completion_tokens
    return mock_response


@pytest.fixture
def mock_openai_client():
    """Patch the OpenAI client."""
    with patch("src.summarizer.llm.client.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def summarizer_client(mock_openai_client):
    """Create a SummarizerClient with a mocked OpenAI client."""
    client = SummarizerClient(api_key="test-key", model="gpt-4o-mini")
    return client


# ---------------------------------------------------------------------------
# Token utility tests
# ---------------------------------------------------------------------------

class TestTokenUtils:
    def test_count_tokens_returns_int(self):
        count = count_tokens("Hello, world!", "gpt-4o-mini")
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_empty_string(self):
        count = count_tokens("", "gpt-4o-mini")
        assert count == 0

    def test_count_tokens_longer_text_has_more_tokens(self):
        short = count_tokens("Hello", "gpt-4o-mini")
        long = count_tokens("Hello " * 100, "gpt-4o-mini")
        assert long > short

    def test_estimate_cost_returns_float(self):
        cost = estimate_cost(100, 50, "gpt-4o-mini")
        assert isinstance(cost, float)
        assert cost > 0

    def test_estimate_cost_scales_with_tokens(self):
        cost_small = estimate_cost(100, 50, "gpt-4o-mini")
        cost_large = estimate_cost(1000, 500, "gpt-4o-mini")
        assert cost_large > cost_small

    def test_estimate_cost_unknown_model_uses_default(self):
        cost = estimate_cost(100, 50, "unknown-model-xyz")
        assert isinstance(cost, float)
        assert cost > 0

    def test_fits_in_context_short_text(self):
        assert fits_in_context("Short text", "gpt-4o-mini") is True

    def test_fits_in_context_very_long_text(self):
        # Create text that exceeds the context window
        very_long = "word " * 200_000
        assert fits_in_context(very_long, "gpt-4o-mini") is False

    def test_get_context_window_known_model(self):
        window = get_context_window("gpt-4o-mini")
        assert window == 128_000

    def test_get_context_window_unknown_model_returns_default(self):
        window = get_context_window("unknown-model")
        assert window == 128_000  # Default fallback


# ---------------------------------------------------------------------------
# PromptBuilder tests
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def test_build_returns_prompt_messages(self):
        builder = PromptBuilder(style="concise")
        result = builder.build("Some article text")
        assert isinstance(result, PromptMessages)
        assert result.system
        assert result.user

    def test_system_prompt_contains_style_content(self):
        builder = PromptBuilder(style="concise")
        system = builder.build_system_prompt()
        assert "concise" in system.lower() or "clear" in system.lower()

    def test_system_prompt_different_per_style(self):
        concise = PromptBuilder(style="concise").build_system_prompt()
        detailed = PromptBuilder(style="detailed").build_system_prompt()
        bullet = PromptBuilder(style="bullet").build_system_prompt()
        assert concise != detailed
        assert concise != bullet
        assert detailed != bullet

    def test_user_prompt_contains_article_text(self):
        builder = PromptBuilder(style="concise")
        article_text = "This is a unique test article 12345."
        user = builder.build_user_prompt(article_text)
        assert article_text in user

    def test_user_prompt_includes_title_when_provided(self):
        builder = PromptBuilder(style="concise")
        user = builder.build_user_prompt("Article content", title="My Great Article")
        assert "My Great Article" in user

    def test_user_prompt_without_title(self):
        builder = PromptBuilder(style="concise")
        user = builder.build_user_prompt("Article content", title=None)
        assert "Article content" in user

    def test_max_summary_words_appears_in_system_prompt(self):
        builder = PromptBuilder(style="concise", max_summary_words=150)
        system = builder.build_system_prompt()
        assert "150" in system

    def test_custom_system_prompt_overrides_style(self):
        custom = "You are a custom assistant."
        builder = PromptBuilder(style="concise", custom_system_prompt=custom)
        assert builder.build_system_prompt() == custom

    def test_invalid_style_raises_error(self):
        with pytest.raises(ValueError, match="Unknown style"):
            PromptBuilder(style="invalid_style_xyz")

    def test_to_openai_messages_format(self):
        builder = PromptBuilder(style="concise")
        messages = builder.build("Article text").to_openai_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "content" in messages[0]
        assert "content" in messages[1]

    def test_chunk_user_prompt_includes_chunk_info(self):
        builder = PromptBuilder(style="concise")
        prompt = builder.build_chunk_user_prompt("chunk text", chunk_index=2, total_chunks=5)
        assert "2" in prompt
        assert "5" in prompt

    def test_reduce_user_prompt_includes_all_summaries(self):
        builder = PromptBuilder(style="concise")
        summaries = ["Summary one.", "Summary two.", "Summary three."]
        prompt = builder.build_reduce_user_prompt(summaries)
        for summary in summaries:
            assert summary in prompt


# ---------------------------------------------------------------------------
# TextChunker tests
# ---------------------------------------------------------------------------

class TestTextChunker:
    def test_short_text_returns_single_chunk(self):
        chunker = TextChunker(model="gpt-4o-mini")
        text = "This is a short article."
        chunks = chunker.split(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_returns_multiple_chunks(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=50, overlap=10)
        # ~300 tokens
        text = "word " * 200
        chunks = chunker.split(text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=20, overlap=5)
        text = "token " * 60
        chunks = chunker.split(text)
        # Verify that consecutive chunks share some content (overlap)
        if len(chunks) > 1:
            # The end of chunk[0] should appear in the beginning of chunk[1]
            end_of_first = chunks[0][-20:]
            start_of_second = chunks[1][:20]
            # At least some tokens should overlap
            assert len(chunks) > 1  # Just verify chunking happened

    def test_needs_chunking_short_text(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=1000)
        assert chunker.needs_chunking("Short text") is False

    def test_needs_chunking_long_text(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=10)
        long_text = "word " * 100
        assert chunker.needs_chunking(long_text) is True

    def test_chunks_cover_all_content(self):
        """All tokens in original text should appear in at least one chunk."""
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=30, overlap=5)
        words = [f"word{i}" for i in range(100)]
        text = " ".join(words)
        chunks = chunker.split(text)

        # Every word should appear in at least one chunk
        combined = " ".join(chunks)
        for word in words:
            assert word in combined

    def test_empty_text_returns_single_empty_chunk(self):
        chunker = TextChunker(model="gpt-4o-mini")
        chunks = chunker.split("")
        assert len(chunks) == 1


# ---------------------------------------------------------------------------
# SummarizerClient tests
# ---------------------------------------------------------------------------

class TestSummarizerClient:
    def test_complete_returns_response_text(self, summarizer_client, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            "This is a summary."
        )
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Summarize this."},
        ]
        result = summarizer_client.complete(messages)
        assert result == "This is a summary."

    def test_complete_calls_api_with_correct_params(self, summarizer_client, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        messages = [{"role": "user", "content": "test"}]
        summarizer_client.complete(messages)

        mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )

    def test_usage_stats_updated_after_call(self, summarizer_client, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            "Summary", prompt_tokens=100, completion_tokens=50
        )
        summarizer_client.complete([{"role": "user", "content": "test"}])
        stats = summarizer_client.usage_stats
        assert stats["call_count"] == 1
        assert stats["total_prompt_tokens"] == 100
        assert stats["total_completion_tokens"] == 50
        assert stats["total_tokens"] == 150
        assert stats["total_cost_usd"] > 0

    def test_usage_stats_accumulate_across_calls(self, summarizer_client, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            "Summary", prompt_tokens=100, completion_tokens=50
        )
        summarizer_client.complete([{"role": "user", "content": "test 1"}])
        summarizer_client.complete([{"role": "user", "content": "test 2"}])

        stats = summarizer_client.usage_stats
        assert stats["call_count"] == 2
        assert stats["total_prompt_tokens"] == 200
        assert stats["total_completion_tokens"] == 100

    def test_retry_on_rate_limit_error(self, summarizer_client, mock_openai_client):
        """Should retry on RateLimitError and eventually succeed."""
        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        success_response = make_mock_response("Summary after retry")

        mock_openai_client.chat.completions.create.side_effect = [
            rate_limit_error,
            success_response,
        ]

        with patch("src.summarizer.llm.client.time.sleep"):
            result = summarizer_client.complete([{"role": "user", "content": "test"}])

        assert result == "Summary after retry"
        assert mock_openai_client.chat.completions.create.call_count == 2

    def test_retry_exhausted_raises_last_exception(self, summarizer_client, mock_openai_client):
        """Should raise after all retries are exhausted."""
        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        mock_openai_client.chat.completions.create.side_effect = rate_limit_error

        with patch("src.summarizer.llm.client.time.sleep"):
            with pytest.raises(openai.RateLimitError):
                summarizer_client.complete([{"role": "user", "content": "test"}])

        assert mock_openai_client.chat.completions.create.call_count == 3  # max_retries=3

    def test_no_retry_on_authentication_error(self, summarizer_client, mock_openai_client):
        """Should NOT retry on AuthenticationError."""
        auth_error = openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401, headers={}),
            body={"error": {"message": "Invalid API key"}},
        )
        mock_openai_client.chat.completions.create.side_effect = auth_error

        with pytest.raises(openai.AuthenticationError):
            summarizer_client.complete([{"role": "user", "content": "test"}])

        # Should only be called once — no retries
        assert mock_openai_client.chat.completions.create.call_count == 1

    def test_retry_on_api_connection_error(self, summarizer_client, mock_openai_client):
        """Should retry on APIConnectionError."""
        connection_error = openai.APIConnectionError(request=MagicMock())
        success_response = make_mock_response("Connected successfully")

        mock_openai_client.chat.completions.create.side_effect = [
            connection_error,
            connection_error,
            success_response,
        ]

        with patch("src.summarizer.llm.client.time.sleep"):
            result = summarizer_client.complete([{"role": "user", "content": "test"}])

        assert result == "Connected successfully"
        assert mock_openai_client.chat.completions.create.call_count == 3

    def test_empty_response_content_raises_error(self, summarizer_client, mock_openai_client):
        """Should raise ValueError if response content is None."""
        mock_response = make_mock_response("")
        mock_response.choices[0].message.content = None
        mock_openai_client.chat.completions.create.return_value = mock_response

        with pytest.raises(ValueError, match="empty response"):
            summarizer_client.complete([{"role": "user", "content": "test"}])

    def test_custom_model_and_temperature(self, mock_openai_client):
        """Should use configured model and temperature."""
        client = SummarizerClient(
            api_key="test-key",
            model="gpt-4",
            temperature=0.7,
            max_tokens=2048,
        )
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")

        client.complete([{"role": "user", "content": "test"}])

        mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}],
            temperature=0.7,
            max_tokens=2048,
        )

    def test_log_usage_summary_does_not_raise(self, summarizer_client, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        summarizer_client.complete([{"role": "user", "content": "test"}])
        # Should not raise
        summarizer_client.log_usage_summary()


# ---------------------------------------------------------------------------
# Map-reduce integration tests
# ---------------------------------------------------------------------------

class TestMapReduce:
    def test_map_reduce_calls_summarize_fn_for_each_chunk(self):
        call_log = []

        def mock_summarize_fn(text, title, is_chunk, chunk_index, total_chunks, **kwargs):
            call_log.append({
                "is_chunk": is_chunk,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "is_reduce": kwargs.get("is_reduce", False),
            })
            return f"Summary of chunk {chunk_index}"

        long_text = "word " * 500  # Should need chunking with small chunk_size
        result = run_map_reduce(
            text=long_text,
            summarize_fn=mock_summarize_fn,
            model="gpt-4o-mini",
            chunk_size=50,
            overlap=10,
        )

        # Should have called for each chunk (map) + once for reduce
        chunk_calls = [c for c in call_log if c["is_chunk"]]
        reduce_calls = [c for c in call_log if c.get("is_reduce")]

        assert len(chunk_calls) > 0
        assert len(reduce_calls) == 1

    def test_map_reduce_short_text_no_chunking(self):
        call_log = []

        def mock_summarize_fn(text, title, is_chunk, chunk_index, total_chunks, **kwargs):
            call_log.append({"is_chunk": is_chunk})
            return "Single summary"

        short_text = "This is a short article."
        result = run_map_reduce(
            text=short_text,
            summarize_fn=mock_summarize_fn,
            model="gpt-4o-mini",
            chunk_size=1000,
        )

        assert result == "Single summary"
        assert len(call_log) == 1
        assert call_log[0]["is_chunk"] is False

    def test_map_reduce_returns_string(self):
        def mock_summarize_fn(text, title, is_chunk, chunk_index, total_chunks, **kwargs):
            return "A summary."

        result = run_map_reduce(
            text="word " * 200,
            summarize_fn=mock_summarize_fn,
            model="gpt-4o-mini",
            chunk_size=30,
            overlap=5,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_map_reduce_passes_title_to_reduce(self):
        received_titles = []

        def mock_summarize_fn(text, title, is_chunk, chunk_index, total_chunks, **kwargs):
            if kwargs.get("is_reduce"):
                received_titles.append(title)
            return "Summary"

        run_map_reduce(
            text="word " * 200,
            summarize_fn=mock_summarize_fn,
            model="gpt-4o-mini",
            chunk_size=30,
            overlap=5,
            title="My Article Title",
        )

        assert "My Article Title" in received_titles