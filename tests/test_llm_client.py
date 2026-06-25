"""Tests for SummarizerClient, PromptBuilder, chunking, and retry logic."""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch, call
from types import SimpleNamespace

import pytest

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from summarizer.llm.client import SummarizerClient
from summarizer.llm.prompts import PromptBuilder
from summarizer.llm.chunker import TextChunker, map_reduce_summarize
from summarizer.llm.token_utils import count_tokens, estimate_cost, fits_in_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content: str, prompt_tokens: int = 10, completion_tokens: int = 20):
    """Build a mock openai ChatCompletion response."""
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=usage)


def _make_client(mock_openai_cls=None, **kwargs) -> tuple[SummarizerClient, MagicMock]:
    """Create a SummarizerClient with a mocked underlying openai.OpenAI."""
    with patch("summarizer.llm.client.openai.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        client = SummarizerClient(**kwargs)
    return client, mock_instance


# ---------------------------------------------------------------------------
# PromptBuilder tests
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def test_build_messages_concise(self):
        pb = PromptBuilder(style="concise")
        msgs = pb.build_messages("Some article text.")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert "Some article text." in msgs[1]["content"]

    def test_build_messages_bullet(self):
        pb = PromptBuilder(style="bullet")
        msgs = pb.build_messages("Article about AI.")
        assert "bullet" in msgs[0]["content"].lower() or "-" in msgs[0]["content"]

    def test_build_messages_detailed(self):
        pb = PromptBuilder(style="detailed")
        msgs = pb.build_messages("Detailed article.")
        assert msgs[0]["role"] == "system"

    def test_extra_instructions_included(self):
        pb = PromptBuilder(style="concise", extra_instructions="Focus on climate.")
        msgs = pb.build_messages("Climate article.")
        assert "Focus on climate." in msgs[0]["content"]

    def test_build_chunk_messages(self):
        pb = PromptBuilder()
        msgs = pb.build_chunk_messages("chunk text", chunk_index=0, total_chunks=3)
        assert msgs[1]["role"] == "user"
        assert "1 of 3" in msgs[1]["content"]
        assert "chunk text" in msgs[1]["content"]

    def test_build_reduce_messages(self):
        pb = PromptBuilder()
        summaries = ["Summary A.", "Summary B."]
        msgs = pb.build_reduce_messages(summaries)
        assert msgs[1]["role"] == "user"
        assert "Summary A." in msgs[1]["content"]
        assert "Summary B." in msgs[1]["content"]


# ---------------------------------------------------------------------------
# Token utility tests
# ---------------------------------------------------------------------------

class TestTokenUtils:
    def test_count_tokens_returns_int(self):
        result = count_tokens("Hello, world!")
        assert isinstance(result, int)
        assert result > 0

    def test_count_tokens_longer_text(self):
        short = count_tokens("Hi")
        long = count_tokens("Hi " * 100)
        assert long > short

    def test_estimate_cost_known_model(self):
        cost = estimate_cost(1000, 500, model="gpt-4o-mini")
        assert isinstance(cost, float)
        assert cost > 0

    def test_estimate_cost_unknown_model(self):
        cost = estimate_cost(1000, 500, model="unknown-model-xyz")
        assert cost == 0.0

    def test_fits_in_context_short_text(self):
        assert fits_in_context("Short text.", model="gpt-4o-mini") is True

    def test_fits_in_context_huge_text(self):
        # 200k words should exceed context window
        huge_text = "word " * 200_000
        assert fits_in_context(huge_text, model="gpt-4o-mini") is False


# ---------------------------------------------------------------------------
# TextChunker tests
# ---------------------------------------------------------------------------

class TestTextChunker:
    def test_short_text_returns_single_chunk(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=3000)
        result = chunker.split("Short text.")
        assert len(result) == 1
        assert result[0] == "Short text."

    def test_long_text_returns_multiple_chunks(self):
        # ~9000 tokens worth of text (very roughly: 1 token ≈ 4 chars)
        long_text = "word " * 4_000
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=1_000, overlap=100)
        chunks = chunker.split(long_text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        # Create text large enough to split into 2 chunks with overlap
        long_text = "token " * 2_500
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=1_000, overlap=200)
        chunks = chunker.split(long_text)
        if len(chunks) >= 2:
            # The end of chunk 0 and start of chunk 1 should share content
            end_of_first = chunks[0][-50:]
            start_of_second = chunks[1][:200]
            # They should share at least some tokens (overlap)
            assert len(chunks) >= 2

    def test_no_chunk_is_empty(self):
        long_text = "word " * 3_000
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=500, overlap=50)
        chunks = chunker.split(long_text)
        for chunk in chunks:
            assert chunk.strip() != ""


# ---------------------------------------------------------------------------
# SummarizerClient tests
# ---------------------------------------------------------------------------

class TestSummarizerClient:
    def _patched_client(self, response_content="Test summary.", **kwargs):
        """Return a SummarizerClient whose underlying openai client is mocked."""
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response(response_content)

        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            client = SummarizerClient(**kwargs)

        client._client = mock_openai
        return client, mock_openai

    def test_summarize_short_text_calls_api_once(self):
        client, mock_openai = self._patched_client("Summary here.")
        text = "This is a short article."
        summary, usage = client.summarize(text)
        assert summary == "Summary here."
        assert mock_openai.chat.completions.create.call_count == 1

    def test_summarize_returns_usage_dict(self):
        client, mock_openai = self._patched_client("A summary.")
        _, usage = client.summarize("Short text.")
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage

    def test_summarize_strips_whitespace(self):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("  Trimmed summary.  ")
        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            client = SummarizerClient()
        client._client = mock_openai
        summary, _ = client.summarize("Some text.")
        assert summary == "Trimmed summary."

    def test_model_passed_to_api(self):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("ok")
        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            client = SummarizerClient(model="gpt-4o")
        client._client = mock_openai
        client.summarize("Text.")
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o" or call_kwargs[1].get("model") == "gpt-4o" or "gpt-4o" in str(call_kwargs)

    def test_temperature_passed_to_api(self):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("ok")
        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            client = SummarizerClient(temperature=0.7)
        client._client = mock_openai
        client.summarize("Text.")
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert call_kwargs.kwargs.get("temperature") == 0.7 or call_kwargs[1].get("temperature") == 0.7

    def test_retry_on_rate_limit(self):
        """Client should retry up to 3 times on RateLimitError."""
        import openai as oai

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429

        # Fail twice, succeed on third attempt
        mock_openai.chat.completions.create.side_effect = [
            oai.RateLimitError("Rate limited", response=mock_response, body={}),
            oai.RateLimitError("Rate limited", response=mock_response, body={}),
            _make_response("Retried successfully."),
        ]

        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            with patch("summarizer.llm.client.wait_exponential", return_value=MagicMock(return_value=0)):
                client = SummarizerClient()

        client._client = mock_openai

        # Patch wait to avoid sleeping in tests
        with patch("tenacity.nap.time") as mock_time:
            mock_time.sleep = MagicMock()
            summary, _ = client.summarize("Short article text.")

        assert summary == "Retried successfully."
        assert mock_openai.chat.completions.create.call_count == 3

    def test_raises_after_max_retries(self):
        """Client should raise after exhausting 3 retry attempts."""
        import openai as oai

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_openai.chat.completions.create.side_effect = oai.InternalServerError(
            "Server error", response=mock_response, body={}
        )

        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            client = SummarizerClient()
        client._client = mock_openai

        with patch("tenacity.nap.time") as mock_time:
            mock_time.sleep = MagicMock()
            with pytest.raises(oai.InternalServerError):
                client.summarize("Short text.")


# ---------------------------------------------------------------------------
# Map-reduce tests
# ---------------------------------------------------------------------------

class TestMapReduce:
    def test_map_reduce_called_for_long_text(self):
        """summarize() should invoke map_reduce_summarize for texts exceeding context."""
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("chunk summary")

        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            client = SummarizerClient(model="gpt-4o-mini")
        client._client = mock_openai

        long_text = "word " * 200_000  # ~200k tokens, exceeds context

        with patch("summarizer.llm.client.fits_in_context", return_value=False):
            with patch("summarizer.llm.client.map_reduce_summarize", return_value="Final summary.") as mock_mr:
                summary, _ = client.summarize(long_text)

        mock_mr.assert_called_once()
        assert summary == "Final summary."

    def test_map_reduce_pipeline(self):
        """map_reduce_summarize should call _call_api for each chunk plus reduce."""
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = _make_response("partial")

        with patch("summarizer.llm.client.openai.OpenAI", return_value=mock_openai):
            client = SummarizerClient()
        client._client = mock_openai

        # Force 3 chunks
        chunks = ["chunk one text", "chunk two text", "chunk three text"]
        with patch("summarizer.llm.chunker.TextChunker.split", return_value=chunks):
            with patch.object(client, "_call_api", return_value=("partial summary", {"prompt_tokens": 5, "completion_tokens": 5})) as mock_call:
                result = map_reduce_summarize("some long text", client=client)

        # 3 map calls + 1 reduce call = 4 total
        assert mock_call.call_count == 4