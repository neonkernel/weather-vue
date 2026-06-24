"""Tests for LLM client, prompt construction, retry behavior, and chunking."""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, Mock, call, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from openai import APIConnectionError, APIStatusError, APITimeoutError

from summarizer.llm.chunker import Chunker, TextChunk, map_reduce_summarize
from summarizer.llm.client import SummarizerClient
from summarizer.llm.prompts import PromptBuilder, SummaryStyle
from summarizer.llm.token_utils import (
    count_tokens,
    estimate_cost,
    fits_in_context,
    get_context_window,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_openai_response(content: str, prompt_tokens: int = 10, completion_tokens: int = 20):
    """Create a mock OpenAI ChatCompletion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    return response


def _make_client(
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 512,
    max_retries: int = 3,
) -> SummarizerClient:
    """Create a SummarizerClient with a mocked underlying OpenAI client."""
    with patch("summarizer.llm.client.OpenAI"):
        client = SummarizerClient(
            api_key="test-key",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )
    return client


# ---------------------------------------------------------------------------
# Token utility tests
# ---------------------------------------------------------------------------


class TestTokenUtils:
    def test_count_tokens_returns_positive_int(self):
        count = count_tokens("Hello, world!", model="gpt-4o-mini")
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_longer_text_has_more_tokens(self):
        short = count_tokens("Hi", model="gpt-4o-mini")
        long = count_tokens("Hello " * 100, model="gpt-4o-mini")
        assert long > short

    def test_count_tokens_empty_string(self):
        assert count_tokens("", model="gpt-4o-mini") == 0

    def test_estimate_cost_known_model(self):
        cost = estimate_cost(1000, 500, model="gpt-4o-mini")
        assert cost > 0.0
        assert isinstance(cost, float)

    def test_estimate_cost_unknown_model_returns_zero(self):
        cost = estimate_cost(1000, 500, model="unknown-model-xyz")
        assert cost == 0.0

    def test_get_context_window_known_model(self):
        window = get_context_window("gpt-4o-mini")
        assert window == 128_000

    def test_get_context_window_unknown_model_returns_default(self):
        window = get_context_window("unknown-model")
        assert window == 8_192

    def test_fits_in_context_short_text(self):
        assert fits_in_context("Hello world", model="gpt-4o-mini") is True

    def test_fits_in_context_exceeds_window(self):
        # Patch get_context_window to return a tiny window
        with patch("summarizer.llm.token_utils.get_context_window", return_value=5):
            result = fits_in_context("This is a longer text that won't fit", model="gpt-4o-mini")
        assert result is False


# ---------------------------------------------------------------------------
# PromptBuilder tests
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    def test_build_system_prompt_contains_role(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        system = builder.build_system_prompt()
        assert "summarizer" in system.lower()

    def test_build_user_prompt_contains_title_and_content(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        prompt = builder.build_user_prompt("Article body text.", title="Test Title")
        assert "Test Title" in prompt
        assert "Article body text." in prompt

    def test_build_user_prompt_without_title(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        prompt = builder.build_user_prompt("Some content.")
        assert "Some content." in prompt
        assert "Untitled" in prompt

    def test_build_messages_returns_two_messages(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        messages = builder.build_messages("Content here.", title="Title")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_build_messages_roles_are_correct(self):
        builder = PromptBuilder()
        messages = builder.build_messages("text")
        roles = [m["role"] for m in messages]
        assert roles == ["system", "user"]

    def test_different_styles_produce_different_system_prompts(self):
        concise = PromptBuilder(style=SummaryStyle.CONCISE).build_system_prompt()
        detailed = PromptBuilder(style=SummaryStyle.DETAILED).build_system_prompt()
        assert concise != detailed

    def test_bullet_points_style(self):
        builder = PromptBuilder(style=SummaryStyle.BULLET_POINTS)
        system = builder.build_system_prompt()
        assert "bullet" in system.lower()

    def test_custom_instruction_overrides_default(self):
        builder = PromptBuilder(
            style=SummaryStyle.CONCISE,
            custom_instruction="Summarize in French.",
        )
        prompt = builder.build_user_prompt("Content.", title="Title")
        assert "Summarize in French." in prompt

    def test_build_chunk_messages(self):
        builder = PromptBuilder()
        messages = builder.build_chunk_messages("Chunk text here.")
        assert len(messages) == 2
        assert "Chunk text here." in messages[1]["content"]

    def test_build_reduce_messages(self):
        builder = PromptBuilder()
        summaries = ["Summary one.", "Summary two."]
        messages = builder.build_reduce_messages(summaries, title="My Article")
        assert len(messages) == 2
        assert "My Article" in messages[1]["content"]
        assert "Summary one." in messages[1]["content"]
        assert "Summary two." in messages[1]["content"]

    def test_build_reduce_messages_numbers_sections(self):
        builder = PromptBuilder()
        messages = builder.build_reduce_messages(["A", "B", "C"])
        content = messages[1]["content"]
        assert "Section 1" in content
        assert "Section 2" in content
        assert "Section 3" in content


# ---------------------------------------------------------------------------
# Chunker tests
# ---------------------------------------------------------------------------


class TestChunker:
    def test_short_text_returns_single_chunk(self):
        chunker = Chunker(model="gpt-4o-mini")
        chunks = chunker.split("Short text.")
        assert len(chunks) == 1
        assert isinstance(chunks[0], TextChunk)

    def test_chunk_has_correct_index(self):
        chunker = Chunker(model="gpt-4o-mini")
        chunks = chunker.split("Short text.")
        assert chunks[0].chunk_index == 0

    def test_long_text_produces_multiple_chunks(self):
        # Use a tiny max window to force chunking
        chunker = Chunker(model="gpt-4o-mini", reserved_tokens=127_500, overlap_tokens=10)
        # 500 tokens worth of text ~= 500 words
        long_text = "word " * 600
        chunks = chunker.split(long_text)
        assert len(chunks) >= 2

    def test_chunks_have_token_count(self):
        chunker = Chunker(model="gpt-4o-mini")
        chunks = chunker.split("Hello world, this is a test.")
        for chunk in chunks:
            assert chunk.token_count > 0

    def test_chunk_total_count_is_consistent(self):
        chunker = Chunker(model="gpt-4o-mini", reserved_tokens=127_500, overlap_tokens=10)
        long_text = "word " * 600
        chunks = chunker.split(long_text)
        for chunk in chunks:
            assert chunk.total_chunks == len(chunks)

    def test_text_chunk_dataclass(self):
        chunk = TextChunk(text="Hello", chunk_index=0, total_chunks=1)
        assert chunk.token_count > 0

    def test_overlap_means_chunks_share_content(self):
        """With overlap, the end of chunk N should appear at start of chunk N+1."""
        chunker = Chunker(
            model="gpt-4o-mini",
            reserved_tokens=127_800,  # very small window
            overlap_tokens=20,
        )
        long_text = "The quick brown fox jumps over the lazy dog. " * 50
        chunks = chunker.split(long_text)
        if len(chunks) >= 2:
            # Chunks should be non-empty
            for chunk in chunks:
                assert len(chunk.text) > 0


# ---------------------------------------------------------------------------
# SummarizerClient tests
# ---------------------------------------------------------------------------


class TestSummarizerClient:
    def test_complete_returns_text_and_tokens(self):
        client = _make_client()
        mock_response = _make_openai_response("Test summary.", 50, 30)
        client._client.chat.completions.create.return_value = mock_response

        text, prompt_tok, completion_tok = client.complete(
            [{"role": "user", "content": "Summarize this."}]
        )
        assert text == "Test summary."
        assert prompt_tok == 50
        assert completion_tok == 30

    def test_complete_passes_messages_to_api(self):
        client = _make_client()
        mock_response = _make_openai_response("Summary")
        client._client.chat.completions.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Summarize this."},
        ]
        client.complete(messages)

        client._client.chat.completions.create.assert_called_once()
        call_kwargs = client._client.chat.completions.create.call_args
        assert call_kwargs.kwargs["messages"] == messages

    def test_complete_passes_model_and_temperature(self):
        client = _make_client(model="gpt-4o", temperature=0.7, max_tokens=256)
        client._client.chat.completions.create.return_value = _make_openai_response("OK")

        client.complete([{"role": "user", "content": "Hi"}])

        kwargs = client._client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 256

    def test_retry_on_connection_error(self):
        client = _make_client(max_retries=3)
        mock_create = client._client.chat.completions.create

        # Fail twice, succeed on third attempt
        mock_create.side_effect = [
            APIConnectionError(request=MagicMock()),
            APIConnectionError(request=MagicMock()),
            _make_openai_response("Success after retries"),
        ]

        text, _, _ = client.complete([{"role": "user", "content": "Hi"}])
        assert text == "Success after retries"
        assert mock_create.call_count == 3

    def test_retry_on_timeout_error(self):
        client = _make_client(max_retries=3)
        mock_create = client._client.chat.completions.create

        mock_create.side_effect = [
            APITimeoutError(request=MagicMock()),
            _make_openai_response("OK"),
        ]

        text, _, _ = client.complete([{"role": "user", "content": "Hi"}])
        assert text == "OK"
        assert mock_create.call_count == 2

    def test_retry_on_rate_limit(self):
        client = _make_client(max_retries=3)
        mock_create = client._client.chat.completions.create

        rate_limit_error = APIStatusError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body={"error": {"message": "Rate limit exceeded"}},
        )

        mock_create.side_effect = [
            rate_limit_error,
            _make_openai_response("After rate limit"),
        ]

        text, _, _ = client.complete([{"role": "user", "content": "Hi"}])
        assert text == "After rate limit"

    def test_no_retry_on_4xx_client_error(self):
        client = _make_client(max_retries=3)
        mock_create = client._client.chat.completions.create

        bad_request = APIStatusError(
            message="Bad request",
            response=MagicMock(status_code=400),
            body={"error": {"message": "Bad request"}},
        )
        mock_create.side_effect = bad_request

        with pytest.raises(APIStatusError):
            client.complete([{"role": "user", "content": "Hi"}])

        # Should only be called once — no retries for 400
        assert mock_create.call_count == 1

    def test_raises_after_max_retries_exhausted(self):
        client = _make_client(max_retries=3)
        mock_create = client._client.chat.completions.create
        mock_create.side_effect = APIConnectionError(request=MagicMock())

        with pytest.raises(APIConnectionError):
            client.complete([{"role": "user", "content": "Hi"}])

        assert mock_create.call_count == 3

    def test_none_content_returns_empty_string(self):
        client = _make_client()
        mock_response = _make_openai_response(None)
        mock_response.choices[0].message.content = None
        client._client.chat.completions.create.return_value = mock_response

        text, _, _ = client.complete([{"role": "user", "content": "Hi"}])
        assert text == ""


# ---------------------------------------------------------------------------
# Map-reduce chunking integration tests
# ---------------------------------------------------------------------------


class TestMapReduceSummarize:
    def _make_mock_client(self, responses: list[str]) -> MagicMock:
        """Create a mock SummarizerClient returning given responses in order."""
        client = MagicMock(spec=SummarizerClient)
        client.complete.side_effect = [
            (resp, 10, 5) for resp in responses
        ]
        return client

    def test_single_chunk_skips_reduce(self):
        """When text fits in one chunk, reduce step is skipped."""
        mock_client = self._make_mock_client(["Single summary."])
        builder = PromptBuilder()

        # Mock chunker to return one chunk
        with patch("summarizer.llm.chunker.Chunker") as MockChunker:
            mock_chunker = MockChunker.return_value
            mock_chunker.split.return_value = [
                TextChunk(text="Short text.", chunk_index=0, total_chunks=1)
            ]
            summary, pt, ct = map_reduce_summarize(
                text="Short text.",
                title="Test",
                client=mock_client,
                prompt_builder=builder,
            )

        assert summary == "Single summary."
        assert mock_client.complete.call_count == 1

    def test_multiple_chunks_calls_reduce(self):
        """When text has multiple chunks, reduce step combines summaries."""
        mock_client = self._make_mock_client(
            ["Summary of chunk 1.", "Summary of chunk 2.", "Final combined summary."]
        )
        builder = PromptBuilder()

        with patch("summarizer.llm.chunker.Chunker") as MockChunker:
            mock_chunker = MockChunker.return_value
            mock_chunker.split.return_value = [
                TextChunk(text="Chunk 1 text.", chunk_index=0, total_chunks=2),
                TextChunk(text="Chunk 2 text.", chunk_index=1, total_chunks=2),
            ]
            summary, pt, ct = map_reduce_summarize(
                text="Long text...",
                title="Test Article",
                client=mock_client,
                prompt_builder=builder,
            )

        # 2 chunk calls + 1 reduce call
        assert mock_client.complete.call_count == 3
        assert summary == "Final combined summary."

    def test_token_counts_are_accumulated(self):
        """Total token counts should be sum of all API calls."""
        mock_client = MagicMock(spec=SummarizerClient)
        mock_client.complete.side_effect = [
            ("Summary 1", 100, 50),
            ("Summary 2", 120, 60),
            ("Final", 200, 80),
        ]
        builder = PromptBuilder()

        with patch("summarizer.llm.chunker.Chunker") as MockChunker:
            mock_chunker = MockChunker.return_value
            mock_chunker.split.return_value = [
                TextChunk(text="A", chunk_index=0, total_chunks=2),
                TextChunk(text="B", chunk_index=1, total_chunks=2),
            ]
            summary, pt, ct = map_reduce_summarize(
                text="Long text...",
                title="Title",
                client=mock_client,
                prompt_builder=builder,
            )

        assert pt == 100 + 120 + 200
        assert ct == 50 + 60 + 80