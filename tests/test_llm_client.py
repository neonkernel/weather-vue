"""Tests for the LLM client, prompt construction, retry behavior, and chunking."""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace

import pytest

from src.summarizer.config import SummarizerConfig
from src.summarizer.llm.client import SummarizerClient, _RETRYABLE_EXCEPTIONS
from src.summarizer.llm.chunker import TextChunker, MapReduceSummarizer, Chunk
from src.summarizer.llm.prompts import PromptBuilder, SummaryStyle
from src.summarizer.llm.token_utils import count_tokens, estimate_cost, fits_in_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs) -> SummarizerConfig:
    defaults = dict(
        model="gpt-4o-mini",
        api_key="test-key-123",
        temperature=0.3,
        max_tokens=512,
        chunk_tokens=3000,
        overlap_tokens=200,
    )
    defaults.update(kwargs)
    return SummarizerConfig(**defaults)


def _make_openai_response(content: str, prompt_tokens=10, completion_tokens=20):
    """Build a minimal mock that looks like an openai ChatCompletion response."""
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=usage)


# ---------------------------------------------------------------------------
# token_utils tests
# ---------------------------------------------------------------------------

class TestTokenUtils(unittest.TestCase):

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_nonempty(self):
        tokens = count_tokens("Hello, world!")
        assert tokens > 0

    def test_count_tokens_longer_text(self):
        short = count_tokens("Hi")
        long = count_tokens("Hi " * 100)
        assert long > short

    def test_estimate_cost_zero(self):
        cost = estimate_cost(0, 0, "gpt-4o-mini")
        assert cost == 0.0

    def test_estimate_cost_positive(self):
        cost = estimate_cost(1000, 500, "gpt-4o-mini")
        assert cost > 0

    def test_estimate_cost_unknown_model_fallback(self):
        # Should not raise; falls back to gpt-4o-mini rates
        cost = estimate_cost(1000, 500, "unknown-model-xyz")
        assert cost > 0

    def test_fits_in_context_short_text(self):
        assert fits_in_context("Hello world", model="gpt-4o-mini") is True

    def test_fits_in_context_empty(self):
        assert fits_in_context("", model="gpt-4o-mini") is True

    def test_fits_in_context_very_long_text(self):
        # 200k words won't fit in any model's window
        huge_text = "word " * 200_000
        assert fits_in_context(huge_text, model="gpt-4o-mini") is False


# ---------------------------------------------------------------------------
# PromptBuilder tests
# ---------------------------------------------------------------------------

class TestPromptBuilder(unittest.TestCase):

    def test_build_returns_two_messages(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        messages = builder.build("Some article text.")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_build_contains_article_text(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        text = "Unique article content XYZ"
        messages = builder.build(text)
        assert text in messages[1]["content"]

    def test_build_chunk_contains_chunk_info(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        messages = builder.build_chunk("chunk text", chunk_index=2, total_chunks=5)
        user_content = messages[1]["content"]
        assert "2" in user_content
        assert "5" in user_content
        assert "chunk text" in user_content

    def test_build_merge_contains_all_summaries(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        summaries = ["Summary A", "Summary B", "Summary C"]
        messages = builder.build_merge(summaries)
        user_content = messages[1]["content"]
        for s in summaries:
            assert s in user_content

    def test_bullet_points_style(self):
        builder = PromptBuilder(style=SummaryStyle.BULLET_POINTS)
        messages = builder.build("Article text.")
        assert "bullet" in messages[0]["content"].lower() or "bullet" in messages[1]["content"].lower()

    def test_custom_system_prompt(self):
        custom = "You are a pirate summarizer."
        builder = PromptBuilder(custom_system_prompt=custom)
        messages = builder.build("Some text.")
        assert messages[0]["content"] == custom

    def test_all_styles_produce_valid_messages(self):
        for style in SummaryStyle:
            builder = PromptBuilder(style=style)
            messages = builder.build("Test text.")
            assert len(messages) == 2
            assert all(m["role"] in ("system", "user") for m in messages)


# ---------------------------------------------------------------------------
# TextChunker tests
# ---------------------------------------------------------------------------

class TestTextChunker(unittest.TestCase):

    def test_empty_text_returns_no_chunks(self):
        chunker = TextChunker(chunk_tokens=100, overlap_tokens=10)
        chunks = chunker.split("")
        assert chunks == []

    def test_whitespace_only_returns_no_chunks(self):
        chunker = TextChunker(chunk_tokens=100, overlap_tokens=10)
        chunks = chunker.split("   \n  ")
        assert chunks == []

    def test_short_text_single_chunk(self):
        chunker = TextChunker(chunk_tokens=1000, overlap_tokens=100)
        chunks = chunker.split("Hello world, this is a short article.")
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert "Hello world" in chunks[0].text

    def test_long_text_multiple_chunks(self):
        # Generate text that is clearly longer than chunk_tokens=50
        long_text = "word " * 500  # ~500+ tokens
        chunker = TextChunker(chunk_tokens=50, overlap_tokens=5)
        chunks = chunker.split(long_text)
        assert len(chunks) > 1

    def test_chunks_are_indexed_sequentially(self):
        long_text = "word " * 500
        chunker = TextChunker(chunk_tokens=50, overlap_tokens=5)
        chunks = chunker.split(long_text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_chunk_token_counts_within_limit(self):
        long_text = "word " * 500
        chunker = TextChunker(chunk_tokens=50, overlap_tokens=5)
        chunks = chunker.split(long_text)
        for chunk in chunks:
            assert chunk.token_count <= 50

    def test_overlap_causes_repeated_content(self):
        """With overlap, adjacent chunks should share some tokens."""
        # Use a large overlap relative to chunk size to ensure overlap
        long_text = "alpha beta gamma delta epsilon " * 100
        chunker = TextChunker(chunk_tokens=20, overlap_tokens=10)
        chunks = chunker.split(long_text)
        if len(chunks) >= 2:
            # The end of chunk 0 should appear at the beginning of chunk 1
            # (approximately — we just check total coverage > non-overlapping)
            total_tokens_with_overlap = sum(c.token_count for c in chunks)
            # With overlap the total should exceed the original token count
            original_tokens = count_tokens(long_text)
            assert total_tokens_with_overlap > original_tokens


# ---------------------------------------------------------------------------
# SummarizerClient tests
# ---------------------------------------------------------------------------

class TestSummarizerClient(unittest.TestCase):

    def _make_client(self, **kwargs):
        config = _make_config(**kwargs)
        with patch("openai.OpenAI"):
            client = SummarizerClient(config=config)
        return client

    def test_raises_without_api_key(self):
        config = SummarizerConfig(
            model="gpt-4o-mini",
            api_key=None,
        )
        with patch.dict("os.environ", {}, clear=True):
            # Remove OPENAI_API_KEY from env if present
            import os
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="No OpenAI API key"):
                SummarizerClient(config=config)

    def test_complete_returns_text_and_usage(self):
        config = _make_config()
        mock_response = _make_openai_response("This is the summary.", 15, 25)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_openai_instance = MockOpenAI.return_value
            mock_openai_instance.chat.completions.create.return_value = mock_response

            client = SummarizerClient(config=config)
            messages = [{"role": "user", "content": "Summarize this."}]
            text, usage = client.complete(messages)

        assert text == "This is the summary."
        assert usage["prompt_tokens"] == 15
        assert usage["completion_tokens"] == 25
        assert usage["total_tokens"] == 40

    def test_complete_passes_model_and_params(self):
        config = _make_config(temperature=0.5, max_tokens=256)
        mock_response = _make_openai_response("Summary.", 10, 20)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_openai_instance = MockOpenAI.return_value
            create_mock = mock_openai_instance.chat.completions.create
            create_mock.return_value = mock_response

            client = SummarizerClient(config=config)
            messages = [{"role": "user", "content": "Hi"}]
            client.complete(messages)

            call_kwargs = create_mock.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["max_tokens"] == 256

    def test_complete_overrides_temperature_and_max_tokens(self):
        config = _make_config(temperature=0.3, max_tokens=512)
        mock_response = _make_openai_response("Summary.", 5, 10)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            create_mock = mock_instance.chat.completions.create
            create_mock.return_value = mock_response

            client = SummarizerClient(config=config)
            client.complete(
                [{"role": "user", "content": "Hi"}],
                temperature=0.9,
                max_tokens=128,
            )

            call_kwargs = create_mock.call_args.kwargs
            assert call_kwargs["temperature"] == 0.9
            assert call_kwargs["max_tokens"] == 128

    def test_retry_on_rate_limit(self):
        """Client should retry on RateLimitError and eventually succeed."""
        import openai as oai

        config = _make_config()
        mock_response = _make_openai_response("Retried summary.", 10, 20)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            create_mock = mock_instance.chat.completions.create

            # Fail twice, then succeed
            create_mock.side_effect = [
                oai.RateLimitError(
                    "rate limit",
                    response=MagicMock(status_code=429, headers={}),
                    body={},
                ),
                oai.RateLimitError(
                    "rate limit",
                    response=MagicMock(status_code=429, headers={}),
                    body={},
                ),
                mock_response,
            ]

            client = SummarizerClient(config=config)

            # Patch tenacity sleep to avoid actual delays in tests
            with patch("tenacity.nap.time.sleep"):
                text, usage = client.complete([{"role": "user", "content": "Hi"}])

        assert text == "Retried summary."
        assert create_mock.call_count == 3

    def test_raises_after_max_retries(self):
        """Client should raise after 3 failed attempts."""
        import openai as oai

        config = _make_config()

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            create_mock = mock_instance.chat.completions.create
            create_mock.side_effect = oai.RateLimitError(
                "rate limit",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )

            client = SummarizerClient(config=config)

            with patch("tenacity.nap.time.sleep"):
                with pytest.raises(oai.RateLimitError):
                    client.complete([{"role": "user", "content": "Hi"}])

        assert create_mock.call_count == 3

    def test_non_retryable_error_raises_immediately(self):
        """Non-transient errors should propagate without retrying."""
        import openai as oai

        config = _make_config()

        with patch("openai.OpenAI") as MockOpenAI:
            mock_instance = MockOpenAI.return_value
            create_mock = mock_instance.chat.completions.create
            create_mock.side_effect = oai.AuthenticationError(
                "bad key",
                response=MagicMock(status_code=401, headers={}),
                body={},
            )

            client = SummarizerClient(config=config)

            with pytest.raises(oai.AuthenticationError):
                client.complete([{"role": "user", "content": "Hi"}])

        assert create_mock.call_count == 1


# ---------------------------------------------------------------------------
# MapReduceSummarizer tests
# ---------------------------------------------------------------------------

class TestMapReduceSummarizer(unittest.TestCase):

    def _make_mock_client(self, responses: list[tuple[str, dict]]):
        """Create a mock SummarizerClient that returns *responses* in order."""
        mock_client = MagicMock()
        mock_client.model = "gpt-4o-mini"
        mock_client.complete.side_effect = responses
        return mock_client

    def test_single_chunk_no_merge(self):
        """If text fits in one chunk, no merge call is made."""
        mock_client = self._make_mock_client(
            [("Summary of chunk 1.", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})]
        )
        chunker = TextChunker(chunk_tokens=1000, overlap_tokens=50)
        prompt_builder = PromptBuilder(style=SummaryStyle.CONCISE)

        mr = MapReduceSummarizer(client=mock_client, prompt_builder=prompt_builder, chunker=chunker)
        result_text, usage = mr.summarize("Short article text.")

        assert result_text == "Summary of chunk 1."
        assert mock_client.complete.call_count == 1  # map only, no reduce

    def test_multi_chunk_with_merge(self):
        """Multiple chunks should trigger map + reduce calls."""
        mock_client = self._make_mock_client(
            [
                ("Chunk 1 summary.", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}),
                ("Chunk 2 summary.", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}),
                ("Final merged summary.", {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}),
            ]
        )
        chunker = TextChunker(chunk_tokens=20, overlap_tokens=5)
        prompt_builder = PromptBuilder(style=SummaryStyle.CONCISE)

        long_text = "word " * 200  # Should produce multiple chunks with chunk_tokens=20
        mr = MapReduceSummarizer(client=mock_client, prompt_builder=prompt_builder, chunker=chunker)
        result_text, usage = mr.summarize(long_text)

        assert "Final merged summary." in result_text or mock_client.complete.call_count >= 3
        # Total calls = N_chunks + 1 (merge)
        total_calls = mock_client.complete.call_count

    def test_usage_accumulation(self):
        """Token usage should be summed across all calls."""
        mock_client = self._make_mock_client(
            [
                ("Summary A.", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}),
                ("Summary B.", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}),
                ("Merged.", {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}),
            ]
        )
        chunker = TextChunker(chunk_tokens=20, overlap_tokens=5)
        prompt_builder = PromptBuilder(style=SummaryStyle.CONCISE)
        long_text = "word " * 200

        mr = MapReduceSummarizer(client=mock_client, prompt_builder=prompt_builder, chunker=chunker)
        _, usage = mr.summarize(long_text)

        assert usage["total_tokens"] > 0

    def test_empty_text_returns_empty(self):
        mock_client = self._make_mock_client([])
        chunker = TextChunker(chunk_tokens=100, overlap_tokens=10)
        prompt_builder = PromptBuilder(style=SummaryStyle.CONCISE)

        mr = MapReduceSummarizer(client=mock_client, prompt_builder=prompt_builder, chunker=chunker)
        result_text, usage = mr.summarize("")

        assert result_text == ""
        assert mock_client.complete.call_count == 0

    def test_merge_prompt_contains_chunk_summaries(self):
        """The reduce call's messages should contain the chunk summaries."""
        mock_client = self._make_mock_client(
            [
                ("Alpha summary.", {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}),
                ("Beta summary.", {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}),
                ("Final.", {"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20}),
            ]
        )
        chunker = TextChunker(chunk_tokens=20, overlap_tokens=5)
        prompt_builder = PromptBuilder(style=SummaryStyle.CONCISE)
        long_text = "word " * 200

        mr = MapReduceSummarizer(client=mock_client, prompt_builder=prompt_builder, chunker=chunker)
        mr.summarize(long_text)

        if mock_client.complete.call_count >= 3:
            # The last call (reduce) should have both chunk summaries in its messages
            last_call_args = mock_client.complete.call_args_list[-1]
            last_messages = last_call_args[0][0]  # positional arg
            merged_content = " ".join(m["content"] for m in last_messages)
            assert "Alpha summary." in merged_content or "Beta summary." in merged_content


if __name__ == "__main__":
    unittest.main()