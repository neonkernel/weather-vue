"""Tests for LLM client, prompt construction, retry behavior, and chunking logic."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock, call
from unittest import mock

import openai

from src.summarizer.config import Config
from src.summarizer.llm.client import SummarizerClient
from src.summarizer.llm.chunker import TextChunker, MapReduceSummarizer
from src.summarizer.llm.prompts import PromptBuilder
from src.summarizer.llm.token_utils import (
    count_tokens,
    estimate_cost,
    fits_in_context,
    get_available_tokens,
    get_context_window,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    """Build a mock OpenAI ChatCompletion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = prompt_tokens + completion_tokens
    return response


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


# ---------------------------------------------------------------------------
# Token Utility Tests
# ---------------------------------------------------------------------------


class TestTokenUtils:
    def test_count_tokens_returns_positive_integer(self):
        text = "Hello, world! This is a test."
        result = count_tokens(text, model="gpt-4o-mini")
        assert isinstance(result, int)
        assert result > 0

    def test_count_tokens_empty_string(self):
        result = count_tokens("", model="gpt-4o-mini")
        assert result == 0

    def test_count_tokens_longer_text_has_more_tokens(self):
        short = "Hello"
        long = "Hello " * 100
        assert count_tokens(long) > count_tokens(short)

    def test_estimate_cost_known_model(self):
        cost = estimate_cost(1000, 500, "gpt-4o-mini")
        assert isinstance(cost, float)
        assert cost > 0

    def test_estimate_cost_zero_tokens(self):
        cost = estimate_cost(0, 0, "gpt-4o-mini")
        assert cost == 0.0

    def test_estimate_cost_unknown_model_falls_back(self):
        # Should not raise; uses gpt-4o-mini pricing as fallback
        cost = estimate_cost(1000, 500, "unknown-model-xyz")
        assert cost > 0

    def test_fits_in_context_short_text(self):
        assert fits_in_context("Short text.", model="gpt-4o-mini") is True

    def test_fits_in_context_very_long_text(self):
        # 200k characters should exceed context window
        long_text = "word " * 40_000
        assert fits_in_context(long_text, model="gpt-4") is False

    def test_get_context_window_known_model(self):
        assert get_context_window("gpt-4o-mini") == 128_000

    def test_get_context_window_unknown_model(self):
        # Should return default
        result = get_context_window("unknown-model")
        assert isinstance(result, int)
        assert result > 0

    def test_get_available_tokens(self):
        available = get_available_tokens("gpt-4o-mini", reserved_tokens=2000)
        assert available == 128_000 - 2000


# ---------------------------------------------------------------------------
# PromptBuilder Tests
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    def test_valid_style_initialization(self):
        for style in ["concise", "detailed", "bullet", "executive"]:
            builder = PromptBuilder(style=style)
            assert builder.style == style

    def test_invalid_style_raises(self):
        with pytest.raises(ValueError, match="Unknown style"):
            PromptBuilder(style="nonexistent_style")

    def test_build_direct_messages_structure(self):
        builder = PromptBuilder(style="concise")
        messages = builder.build_direct_messages("Some article text.", title="Test Article")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_build_direct_messages_contains_article_text(self):
        builder = PromptBuilder(style="concise")
        text = "This is the article content."
        messages = builder.build_direct_messages(text)
        user_content = messages[1]["content"]
        assert text in user_content

    def test_build_direct_messages_with_title(self):
        builder = PromptBuilder(style="concise")
        messages = builder.build_direct_messages("Text here.", title="My Title")
        user_content = messages[1]["content"]
        assert "My Title" in user_content

    def test_build_direct_messages_without_title(self):
        builder = PromptBuilder(style="concise")
        messages = builder.build_direct_messages("Text here.")
        # Should not raise; title is optional
        assert len(messages) == 2

    def test_build_chunk_messages_structure(self):
        builder = PromptBuilder(style="concise")
        messages = builder.build_chunk_messages("Chunk text", chunk_index=0, total_chunks=3)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_build_chunk_messages_contains_section_info(self):
        builder = PromptBuilder(style="concise")
        messages = builder.build_chunk_messages("Chunk text", chunk_index=1, total_chunks=5)
        user_content = messages[1]["content"]
        assert "2" in user_content  # chunk_index + 1
        assert "5" in user_content  # total_chunks

    def test_build_merge_messages_structure(self):
        builder = PromptBuilder(style="concise")
        summaries = ["Summary 1", "Summary 2", "Summary 3"]
        messages = builder.build_merge_messages(summaries, title="Test")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_build_merge_messages_contains_summaries(self):
        builder = PromptBuilder(style="concise")
        summaries = ["First chunk summary.", "Second chunk summary."]
        messages = builder.build_merge_messages(summaries)
        user_content = messages[1]["content"]
        for summary in summaries:
            assert summary in user_content

    def test_system_prompt_varies_by_style(self):
        messages_concise = PromptBuilder("concise").build_direct_messages("text")
        messages_detailed = PromptBuilder("detailed").build_direct_messages("text")
        assert messages_concise[0]["content"] != messages_detailed[0]["content"]


# ---------------------------------------------------------------------------
# TextChunker Tests
# ---------------------------------------------------------------------------


class TestTextChunker:
    def test_short_text_returns_single_chunk(self):
        chunker = TextChunker(model="gpt-4o-mini", max_chunk_tokens=4000)
        text = "This is a short text."
        chunks = chunker.split(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits_into_multiple_chunks(self):
        chunker = TextChunker(model="gpt-4o-mini", max_chunk_tokens=50, overlap_tokens=10)
        # ~500 tokens of text
        text = "word " * 200
        chunks = chunker.split(text)
        assert len(chunks) > 1

    def test_chunks_cover_all_content(self):
        """Verify that all tokens from the original text appear in at least one chunk."""
        chunker = TextChunker(model="gpt-4o-mini", max_chunk_tokens=50, overlap_tokens=5)
        words = [f"word{i}" for i in range(200)]
        text = " ".join(words)
        chunks = chunker.split(text)

        # Every word should appear in at least one chunk
        all_chunk_text = " ".join(chunks)
        for word in words:
            assert word in all_chunk_text

    def test_overlap_creates_duplicate_content(self):
        """With overlap, adjacent chunks should share some tokens."""
        chunker = TextChunker(model="gpt-4o-mini", max_chunk_tokens=30, overlap_tokens=10)
        text = "word " * 100
        chunks = chunker.split(text)

        if len(chunks) >= 2:
            # The end of chunk 0 and beginning of chunk 1 should share tokens
            # This is verified by checking that chunk 1 starts before where chunk 0 ended
            total_unique = count_tokens(text, "gpt-4o-mini")
            total_in_chunks = sum(count_tokens(c, "gpt-4o-mini") for c in chunks)
            assert total_in_chunks > total_unique  # overlap means more total tokens

    def test_invalid_overlap_raises(self):
        with pytest.raises(ValueError):
            chunker = TextChunker(max_chunk_tokens=10, overlap_tokens=15)
            chunker.split("word " * 100)

    def test_chunk_size_does_not_exceed_max(self):
        chunker = TextChunker(model="gpt-4o-mini", max_chunk_tokens=50, overlap_tokens=5)
        text = "word " * 500
        chunks = chunker.split(text)
        for chunk in chunks:
            assert count_tokens(chunk, "gpt-4o-mini") <= 50


# ---------------------------------------------------------------------------
# SummarizerClient Tests
# ---------------------------------------------------------------------------


class TestSummarizerClient:
    def _make_client(self, **kwargs):
        config = make_config(**kwargs)
        with patch("src.summarizer.llm.client.OpenAI"):
            client = SummarizerClient(config=config)
        return client

    def test_initialization(self):
        client = self._make_client()
        assert client.model == "gpt-4o-mini"
        assert client.temperature == 0.3
        assert client.max_tokens == 1024

    def test_complete_returns_string(self):
        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_openai_instance = MockOpenAI.return_value
            mock_openai_instance.chat.completions.create.return_value = make_mock_response(
                "Test summary output."
            )
            client = SummarizerClient(config=make_config())

        client._client = mock_openai_instance
        messages = [{"role": "user", "content": "Summarize this."}]
        result = client.complete(messages)
        assert result == "Test summary output."

    def test_complete_calls_api_with_correct_params(self):
        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = make_mock_response("Result")
            client = SummarizerClient(config=make_config())

        client._client = mock_instance
        messages = [{"role": "user", "content": "Hello"}]
        client.complete(messages)

        mock_instance.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )

    def test_complete_strips_whitespace(self):
        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = make_mock_response(
                "  Summary with whitespace.  "
            )
            client = SummarizerClient(config=make_config())

        client._client = mock_instance
        result = client.complete([{"role": "user", "content": "test"}])
        assert result == "Summary with whitespace."

    def test_complete_raises_on_none_content(self):
        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = make_mock_response(None)
            client = SummarizerClient(config=make_config())

        client._client = mock_instance
        with pytest.raises(ValueError, match="empty response"):
            client.complete([{"role": "user", "content": "test"}])

    def test_retry_on_rate_limit_error(self):
        """Client should retry up to 3 times on RateLimitError."""
        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.side_effect = [
                openai.RateLimitError(
                    "Rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body={"error": {"message": "Rate limit exceeded"}},
                ),
                openai.RateLimitError(
                    "Rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body={"error": {"message": "Rate limit exceeded"}},
                ),
                make_mock_response("Success after retries"),
            ]
            client = SummarizerClient(config=make_config())

        client._client = mock_instance

        # Patch tenacity wait to avoid actual sleeping in tests
        with patch("tenacity.nap.time.sleep"):
            result = client.complete([{"role": "user", "content": "test"}])

        assert result == "Success after retries"
        assert mock_instance.chat.completions.create.call_count == 3

    def test_retry_exhausted_raises_exception(self):
        """After 3 failed attempts, the original exception should be raised."""
        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.side_effect = openai.RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body={"error": {"message": "Rate limit exceeded"}},
            )
            client = SummarizerClient(config=make_config())

        client._client = mock_instance

        with patch("tenacity.nap.time.sleep"):
            with pytest.raises(openai.RateLimitError):
                client.complete([{"role": "user", "content": "test"}])

        assert mock_instance.chat.completions.create.call_count == 3

    def test_non_retryable_error_not_retried(self):
        """Non-transient errors (e.g., AuthenticationError) should not be retried."""
        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.side_effect = openai.AuthenticationError(
                "Invalid API key",
                response=MagicMock(status_code=401),
                body={"error": {"message": "Invalid API key"}},
            )
            client = SummarizerClient(config=make_config())

        client._client = mock_instance

        with pytest.raises(openai.AuthenticationError):
            client.complete([{"role": "user", "content": "test"}])

        # Should only be called once (no retries)
        assert mock_instance.chat.completions.create.call_count == 1

    def test_complete_with_model_override(self):
        with patch("src.summarizer.llm.client.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            mock_instance.chat.completions.create.return_value = make_mock_response("Result")
            client = SummarizerClient(config=make_config())

        client._client = mock_instance
        client.complete(
            [{"role": "user", "content": "test"}],
            model="gpt-4o",
            temperature=0.7,
            max_tokens=512,
        )
        call_kwargs = mock_instance.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 512


# ---------------------------------------------------------------------------
# MapReduceSummarizer Tests
# ---------------------------------------------------------------------------


class TestMapReduceSummarizer:
    def _make_mock_client(self, responses: list[str]) -> MagicMock:
        client = MagicMock(spec=SummarizerClient)
        client.model = "gpt-4o-mini"
        client.complete.side_effect = responses
        return client

    def test_single_chunk_calls_merge(self):
        """Even with 1 chunk, map-reduce should produce a final merge call."""
        mock_client = self._make_mock_client(["Chunk 1 summary.", "Final merged summary."])
        prompt_builder = PromptBuilder(style="concise")
        chunker = TextChunker(model="gpt-4o-mini", max_chunk_tokens=10000)

        summarizer = MapReduceSummarizer(
            client=mock_client,
            prompt_builder=prompt_builder,
            chunker=chunker,
        )
        text = "This is a short article."
        result = summarizer.summarize(text)

        assert result == "Final merged summary."
        assert mock_client.complete.call_count == 2

    def test_multiple_chunks(self):
        """Should summarize each chunk then merge."""
        mock_client = self._make_mock_client([
            "Summary of chunk 1.",
            "Summary of chunk 2.",
            "Summary of chunk 3.",
            "Final merged summary.",
        ])
        prompt_builder = PromptBuilder(style="concise")

        # Force 3 chunks by using small chunk size
        chunker = MagicMock(spec=TextChunker)
        chunker.split.return_value = ["chunk1 text", "chunk2 text", "chunk3 text"]

        summarizer = MapReduceSummarizer(
            client=mock_client,
            prompt_builder=prompt_builder,
            chunker=chunker,
        )
        result = summarizer.summarize("Long article text", title="Test Article")

        assert result == "Final merged summary."
        # 3 chunk calls + 1 merge call
        assert mock_client.complete.call_count == 4

    def test_merge_receives_chunk_summaries(self):
        """The merge call should receive all chunk summaries."""
        chunk_summaries_captured = []

        def capture_merge_call(messages):
            user_content = messages[1]["content"]
            return "Final summary."

        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.model = "gpt-4o-mini"
        mock_client.complete.side_effect = [
            "Summary A.",
            "Summary B.",
            "Final summary.",
        ]

        prompt_builder = PromptBuilder(style="concise")
        chunker = MagicMock(spec=TextChunker)
        chunker.split.return_value = ["chunk1", "chunk2"]

        summarizer = MapReduceSummarizer(
            client=mock_client,
            prompt_builder=prompt_builder,
            chunker=chunker,
        )
        result = summarizer.summarize("text", title="Test")

        assert result == "Final summary."

        # Verify the merge call included both chunk summaries
        merge_call_messages = mock_client.complete.call_args_list[2][0][0]
        user_content = merge_call_messages[1]["content"]
        assert "Summary A." in user_content
        assert "Summary B." in user_content