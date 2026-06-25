"""Tests for LLM client, prompt construction, retry behavior, and chunking logic."""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock, call
from dataclasses import dataclass
from typing import Optional

import openai

from src.summarizer.llm.client import SummarizerClient
from src.summarizer.llm.prompts import PromptBuilder, SummaryStyle
from src.summarizer.llm.chunker import TextChunker, MapReduceSummarizer
from src.summarizer.llm.token_utils import count_tokens, estimate_cost, fits_in_context


# ---------------------------------------------------------------------------
# Helpers / Factories
# ---------------------------------------------------------------------------

def _make_openai_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    """Create a mock OpenAI ChatCompletion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = prompt_tokens + completion_tokens
    return response


def _make_client(mock_openai_cls, response_content="Test summary.", **kwargs):
    """Create a SummarizerClient with a mocked underlying OpenAI client."""
    mock_openai_instance = MagicMock()
    mock_openai_cls.return_value = mock_openai_instance
    mock_openai_instance.chat.completions.create.return_value = _make_openai_response(response_content)
    client = SummarizerClient(api_key="test-key", **kwargs)
    return client, mock_openai_instance


# ---------------------------------------------------------------------------
# Token Utility Tests
# ---------------------------------------------------------------------------

class TestTokenUtils(unittest.TestCase):

    def test_count_tokens_returns_positive_integer(self):
        text = "The quick brown fox jumps over the lazy dog."
        count = count_tokens(text)
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_count_tokens_empty_string(self):
        self.assertEqual(count_tokens(""), 0)

    def test_count_tokens_longer_text_has_more_tokens(self):
        short = "Hello world."
        long = "Hello world. " * 100
        self.assertGreater(count_tokens(long), count_tokens(short))

    def test_count_tokens_different_models(self):
        text = "Sample text for token counting."
        count_mini = count_tokens(text, model="gpt-4o-mini")
        count_gpt4 = count_tokens(text, model="gpt-4")
        # Both should return reasonable positive integers
        self.assertGreater(count_mini, 0)
        self.assertGreater(count_gpt4, 0)

    def test_estimate_cost_known_model(self):
        cost = estimate_cost(1000, 500, model="gpt-4o-mini")
        self.assertGreater(cost, 0)
        # 1000 prompt tokens at $0.000150/1k + 500 completion at $0.000600/1k
        expected = (1000 / 1000 * 0.000150) + (500 / 1000 * 0.000600)
        self.assertAlmostEqual(cost, expected, places=8)

    def test_estimate_cost_unknown_model_falls_back(self):
        # Should not raise, falls back to gpt-4o-mini pricing
        cost = estimate_cost(1000, 500, model="unknown-model-xyz")
        self.assertGreater(cost, 0)

    def test_fits_in_context_short_text(self):
        short_text = "Short article."
        self.assertTrue(fits_in_context(short_text, model="gpt-4o-mini"))

    def test_fits_in_context_very_long_text(self):
        # Generate text that would exceed context window
        very_long = "word " * 200_000  # ~200k tokens, exceeds gpt-4 8k window
        self.assertFalse(fits_in_context(very_long, model="gpt-4"))

    def test_fits_in_context_respects_reserved_tokens(self):
        # With a huge reservation, even short text shouldn't fit
        short_text = "Hi."
        # Reserve basically everything
        self.assertFalse(fits_in_context(short_text, model="gpt-4o-mini", reserved_tokens=200_000))


# ---------------------------------------------------------------------------
# PromptBuilder Tests
# ---------------------------------------------------------------------------

class TestPromptBuilder(unittest.TestCase):

    def test_build_messages_returns_two_messages(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        messages = builder.build_messages("Article text here.")
        self.assertEqual(len(messages), 2)

    def test_build_messages_roles(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        messages = builder.build_messages("Article text.")
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")

    def test_build_messages_contains_article_text(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        article = "This is the article content."
        messages = builder.build_messages(article)
        self.assertIn(article, messages[1]["content"])

    def test_build_messages_different_styles_have_different_system_prompts(self):
        concise = PromptBuilder(style=SummaryStyle.CONCISE).build_messages("text")
        detailed = PromptBuilder(style=SummaryStyle.DETAILED).build_messages("text")
        self.assertNotEqual(concise[0]["content"], detailed[0]["content"])

    def test_build_chunk_messages_includes_chunk_info(self):
        builder = PromptBuilder(style=SummaryStyle.CONCISE)
        messages = builder.build_chunk_messages("Chunk text", chunk_index=1, total_chunks=3)
        self.assertIn("2", messages[1]["content"])  # 1-indexed
        self.assertIn("3", messages[1]["content"])

    def test_build_chunk_messages_returns_two_messages(self):
        builder = PromptBuilder()
        messages = builder.build_chunk_messages("text", 0, 2)
        self.assertEqual(len(messages), 2)

    def test_build_merge_messages_contains_all_summaries(self):
        builder = PromptBuilder()
        summaries = ["Summary one.", "Summary two.", "Summary three."]
        messages = builder.build_merge_messages(summaries)
        content = messages[1]["content"]
        for s in summaries:
            self.assertIn(s, content)

    def test_build_merge_messages_returns_two_messages(self):
        builder = PromptBuilder()
        messages = builder.build_merge_messages(["s1", "s2"])
        self.assertEqual(len(messages), 2)

    def test_all_styles_produce_valid_messages(self):
        for style in SummaryStyle:
            builder = PromptBuilder(style=style)
            messages = builder.build_messages("Some article text.")
            self.assertEqual(len(messages), 2)
            self.assertTrue(messages[0]["content"])
            self.assertTrue(messages[1]["content"])


# ---------------------------------------------------------------------------
# SummarizerClient Tests
# ---------------------------------------------------------------------------

class TestSummarizerClientInit(unittest.TestCase):

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_init_with_explicit_api_key(self, mock_openai_cls):
        mock_openai_cls.return_value = MagicMock()
        client = SummarizerClient(api_key="test-key-123")
        self.assertEqual(client.model, "gpt-4o-mini")

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_init_with_env_api_key(self, mock_openai_cls):
        mock_openai_cls.return_value = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "env-key-456"}):
            client = SummarizerClient()
            self.assertIsNotNone(client)

    def test_init_without_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove OPENAI_API_KEY if set
            import os
            env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
            with patch.dict("os.environ", env, clear=True):
                with self.assertRaises(ValueError):
                    SummarizerClient(api_key=None)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_custom_model_and_temperature(self, mock_openai_cls):
        mock_openai_cls.return_value = MagicMock()
        client = SummarizerClient(api_key="key", model="gpt-4o", temperature=0.7)
        self.assertEqual(client.model, "gpt-4o")
        self.assertEqual(client.temperature, 0.7)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_custom_base_url(self, mock_openai_cls):
        mock_openai_cls.return_value = MagicMock()
        SummarizerClient(api_key="key", base_url="https://custom.api.endpoint/v1")
        call_kwargs = mock_openai_cls.call_args[1]
        self.assertEqual(call_kwargs["base_url"], "https://custom.api.endpoint/v1")


class TestSummarizerClientComplete(unittest.TestCase):

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_complete_returns_text_and_usage(self, mock_openai_cls):
        client, mock_openai = _make_client(mock_openai_cls, response_content="Great summary.")
        messages = [{"role": "user", "content": "Summarize this."}]
        text, usage = client.complete(messages)
        self.assertEqual(text, "Great summary.")
        self.assertIn("prompt_tokens", usage)
        self.assertIn("completion_tokens", usage)
        self.assertIn("total_tokens", usage)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_complete_passes_correct_params_to_api(self, mock_openai_cls):
        client, mock_openai = _make_client(mock_openai_cls)
        messages = [{"role": "system", "content": "You are helpful."}, {"role": "user", "content": "Hi"}]
        client.complete(messages)

        mock_openai.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "gpt-4o-mini")
        self.assertEqual(call_kwargs["messages"], messages)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_complete_usage_totals(self, mock_openai_cls):
        client, mock_openai = _make_client(mock_openai_cls)
        mock_openai.chat.completions.create.return_value = _make_openai_response(
            "Summary", prompt_tokens=200, completion_tokens=75
        )
        _, usage = client.complete([{"role": "user", "content": "test"}])
        self.assertEqual(usage["prompt_tokens"], 200)
        self.assertEqual(usage["completion_tokens"], 75)
        self.assertEqual(usage["total_tokens"], 275)


class TestSummarizerClientRetry(unittest.TestCase):

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_retries_on_rate_limit_error(self, mock_openai_cls):
        client, mock_openai = _make_client(mock_openai_cls)

        # Fail twice, succeed on third attempt
        mock_openai.chat.completions.create.side_effect = [
            openai.RateLimitError("Rate limited", response=MagicMock(), body={}),
            openai.RateLimitError("Rate limited", response=MagicMock(), body={}),
            _make_openai_response("Success after retry"),
        ]

        with patch("tenacity.nap.time"):  # Skip actual sleep
            text, usage = client.complete([{"role": "user", "content": "test"}])

        self.assertEqual(text, "Success after retry")
        self.assertEqual(mock_openai.chat.completions.create.call_count, 3)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_retries_on_connection_error(self, mock_openai_cls):
        client, mock_openai = _make_client(mock_openai_cls)

        mock_openai.chat.completions.create.side_effect = [
            openai.APIConnectionError(request=MagicMock()),
            _make_openai_response("Recovered"),
        ]

        with patch("tenacity.nap.time"):
            text, _ = client.complete([{"role": "user", "content": "test"}])

        self.assertEqual(text, "Recovered")
        self.assertEqual(mock_openai.chat.completions.create.call_count, 2)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_raises_after_max_retries(self, mock_openai_cls):
        client, mock_openai = _make_client(mock_openai_cls)

        mock_openai.chat.completions.create.side_effect = openai.RateLimitError(
            "Persistent rate limit", response=MagicMock(), body={}
        )

        with patch("tenacity.nap.time"):
            with self.assertRaises(openai.RateLimitError):
                client.complete([{"role": "user", "content": "test"}])

        self.assertEqual(mock_openai.chat.completions.create.call_count, 3)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_does_not_retry_on_authentication_error(self, mock_openai_cls):
        client, mock_openai = _make_client(mock_openai_cls)

        mock_openai.chat.completions.create.side_effect = openai.AuthenticationError(
            "Invalid API key", response=MagicMock(), body={}
        )

        with self.assertRaises(openai.AuthenticationError):
            client.complete([{"role": "user", "content": "test"}])

        # Should NOT retry auth errors
        self.assertEqual(mock_openai.chat.completions.create.call_count, 1)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_retries_on_internal_server_error(self, mock_openai_cls):
        client, mock_openai = _make_client(mock_openai_cls)

        mock_openai.chat.completions.create.side_effect = [
            openai.InternalServerError("Server error", response=MagicMock(), body={}),
            _make_openai_response("Recovered from 500"),
        ]

        with patch("tenacity.nap.time"):
            text, _ = client.complete([{"role": "user", "content": "test"}])

        self.assertEqual(text, "Recovered from 500")


# ---------------------------------------------------------------------------
# TextChunker Tests
# ---------------------------------------------------------------------------

class TestTextChunker(unittest.TestCase):

    def test_short_text_returns_single_chunk(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=1000)
        text = "This is a short article."
        chunks = chunker.split(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].index, 0)
        self.assertEqual(chunks[0].text, text)

    def test_long_text_returns_multiple_chunks(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=50, overlap_tokens=5)
        # Generate ~500 tokens of text
        text = " ".join([f"word{i}" for i in range(300)])
        chunks = chunker.split(text)
        self.assertGreater(len(chunks), 1)

    def test_chunks_have_sequential_indices(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=50, overlap_tokens=5)
        text = " ".join([f"word{i}" for i in range(300)])
        chunks = chunker.split(text)
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk.index, i)

    def test_chunk_token_counts_are_reasonable(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=100, overlap_tokens=10)
        text = " ".join([f"token{i}" for i in range(500)])
        chunks = chunker.split(text)
        for chunk in chunks:
            self.assertLessEqual(chunk.token_count, 105)  # Allow small margin
            self.assertGreater(chunk.token_count, 0)

    def test_needs_chunking_short_text(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=1000)
        self.assertFalse(chunker.needs_chunking("Short text."))

    def test_needs_chunking_long_text(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=10)
        long_text = " ".join(["word"] * 100)
        self.assertTrue(chunker.needs_chunking(long_text))

    def test_empty_text_returns_single_chunk(self):
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=100)
        chunks = chunker.split("")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "")


# ---------------------------------------------------------------------------
# MapReduceSummarizer Tests
# ---------------------------------------------------------------------------

class TestMapReduceSummarizer(unittest.TestCase):

    def _make_mock_client(self, responses):
        """Create a mock client that returns predefined responses."""
        client = MagicMock()
        client.complete.side_effect = [
            (resp, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
            for resp in responses
        ]
        return client

    def test_single_chunk_calls_client_twice(self):
        """For 1 chunk: 1 map call + 1 reduce call = 2 total."""
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=1000)
        builder = PromptBuilder()
        # Short text => 1 chunk
        client = self._make_mock_client(["Chunk summary.", "Final summary."])
        mr = MapReduceSummarizer(client, builder, chunker)
        result, usage = mr.summarize("Short article text.")
        self.assertEqual(result, "Final summary.")
        self.assertEqual(client.complete.call_count, 2)

    def test_multi_chunk_aggregates_usage(self):
        """Usage should be aggregated across all API calls."""
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=20, overlap_tokens=2)
        builder = PromptBuilder()
        text = " ".join([f"word{i}" for i in range(200)])

        chunks = chunker.split(text)
        num_chunks = len(chunks)
        # responses: one per chunk + one for merge
        responses = [f"Chunk {i} summary." for i in range(num_chunks)] + ["Final merged summary."]
        client = self._make_mock_client(responses)

        mr = MapReduceSummarizer(client, builder, chunker)
        result, usage = mr.summarize(text)

        total_calls = num_chunks + 1  # map calls + reduce call
        self.assertEqual(client.complete.call_count, total_calls)
        self.assertEqual(usage["total_tokens"], 150 * total_calls)
        self.assertEqual(result, "Final merged summary.")

    def test_merge_receives_all_chunk_summaries(self):
        """The merge call should receive summaries from all chunks."""
        chunker = TextChunker(model="gpt-4o-mini", chunk_size=20, overlap_tokens=2)
        builder = PromptBuilder()
        text = " ".join([f"word{i}" for i in range(200)])

        chunks = chunker.split(text)
        num_chunks = len(chunks)
        chunk_summaries = [f"Summary of section {i}." for i in range(num_chunks)]
        responses = chunk_summaries + ["Final summary."]
        client = self._make_mock_client(responses)

        mr = MapReduceSummarizer(client, builder, chunker)
        mr.summarize(text)

        # The last call should be the merge call
        last_call_args = client.complete.call_args_list[-1][0][0]
        merge_content = last_call_args[1]["content"]
        for s in chunk_summaries:
            self.assertIn(s, merge_content)


if __name__ == "__main__":
    unittest.main()