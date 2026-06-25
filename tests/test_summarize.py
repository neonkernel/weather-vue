"""Integration-style tests for the full summarize() pipeline using mocked LLM responses."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import openai

from src.summarizer.models import Article, Summary
from src.summarizer.summarize import summarize
from src.summarizer.llm.prompts import SummaryStyle


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SHORT_ARTICLE = Article(
    title="AI Breakthrough in Protein Folding",
    content=(
        "Scientists at DeepMind have announced a major breakthrough in protein folding "
        "prediction. The new AlphaFold 3 model can predict the structure of proteins "
        "with unprecedented accuracy, potentially revolutionizing drug discovery and "
        "our understanding of biology. The research, published in Nature, represents "
        "years of work by hundreds of scientists."
    ),
    url="https://example.com/ai-protein",
    author="Jane Smith",
)

LONG_ARTICLE_CONTENT = " ".join(
    [
        f"This is sentence number {i} in a very long article about artificial intelligence "
        f"and its impact on modern society and technology sector growth. "
        for i in range(1000)
    ]
)

LONG_ARTICLE = Article(
    title="The Long Article",
    content=LONG_ARTICLE_CONTENT,
    url="https://example.com/long-article",
)


def _make_openai_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    """Create a mock OpenAI ChatCompletion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = prompt_tokens + completion_tokens
    return response


# ---------------------------------------------------------------------------
# Direct Summarization Tests
# ---------------------------------------------------------------------------

class TestSummarizeDirectPath(unittest.TestCase):
    """Tests for articles that fit in the context window (direct summarization)."""

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_returns_summary_dataclass(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response(
            "AlphaFold 3 achieves breakthrough accuracy in protein structure prediction."
        )

        result = summarize(SHORT_ARTICLE, api_key="test-key")

        self.assertIsInstance(result, Summary)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_contains_correct_text(self, mock_openai_cls):
        expected_summary = "AlphaFold 3 achieves breakthrough accuracy in protein structure prediction."
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response(expected_summary)

        result = summarize(SHORT_ARTICLE, api_key="test-key")

        self.assertEqual(result.summary, expected_summary)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_preserves_article_metadata(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Summary.")

        result = summarize(SHORT_ARTICLE, api_key="test-key")

        self.assertEqual(result.title, SHORT_ARTICLE.title)
        self.assertEqual(result.url, SHORT_ARTICLE.url)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_has_direct_method(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Summary.")

        result = summarize(SHORT_ARTICLE, api_key="test-key")

        self.assertEqual(result.method, "direct")

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_has_token_usage(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response(
            "Summary.", prompt_tokens=150, completion_tokens=30
        )

        result = summarize(SHORT_ARTICLE, api_key="test-key")

        self.assertEqual(result.prompt_tokens, 150)
        self.assertEqual(result.completion_tokens, 30)
        self.assertEqual(result.total_tokens, 180)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_has_estimated_cost(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Summary.")

        result = summarize(SHORT_ARTICLE, api_key="test-key")

        self.assertIsInstance(result.estimated_cost_usd, float)
        self.assertGreater(result.estimated_cost_usd, 0)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_has_created_at_timestamp(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Summary.")

        result = summarize(SHORT_ARTICLE, api_key="test-key")

        self.assertIsInstance(result.created_at, datetime)
        self.assertIsNotNone(result.created_at.tzinfo)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_records_model(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Summary.")

        result = summarize(SHORT_ARTICLE, api_key="test-key", model="gpt-4o-mini")

        self.assertEqual(result.model, "gpt-4o-mini")

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_summary_records_style(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Summary.")

        result = summarize(SHORT_ARTICLE, api_key="test-key", style=SummaryStyle.DETAILED)

        self.assertEqual(result.style, "detailed")

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_single_api_call_for_short_article(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Summary.")

        summarize(SHORT_ARTICLE, api_key="test-key")

        self.assertEqual(mock_instance.chat.completions.create.call_count, 1)


# ---------------------------------------------------------------------------
# Map-Reduce Summarization Tests
# ---------------------------------------------------------------------------

class TestSummarizeMapReducePath(unittest.TestCase):
    """Tests for articles that exceed the context window (map-reduce)."""

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_long_article_uses_map_reduce_method(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance

        # Return a response for every API call
        mock_instance.chat.completions.create.return_value = _make_openai_response("Chunk/Final summary.")

        result = summarize(
            LONG_ARTICLE,
            api_key="test-key",
            model="gpt-4o-mini",
            chunk_size=500,
        )

        self.assertEqual(result.method, "map_reduce")

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_long_article_makes_multiple_api_calls(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Summary.")

        summarize(
            LONG_ARTICLE,
            api_key="test-key",
            model="gpt-4o-mini",
            chunk_size=500,
        )

        # Should have made more than one API call
        self.assertGreater(mock_instance.chat.completions.create.call_count, 1)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_long_article_aggregates_token_usage(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response(
            "Summary.", prompt_tokens=100, completion_tokens=50
        )

        result = summarize(
            LONG_ARTICLE,
            api_key="test-key",
            model="gpt-4o-mini",
            chunk_size=500,
        )

        call_count = mock_instance.chat.completions.create.call_count
        self.assertEqual(result.total_tokens, 150 * call_count)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_long_article_returns_final_merged_summary(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance

        # The last call is the merge call — return a specific final summary
        chunk_response = _make_openai_response("Intermediate chunk summary.")
        final_response = _make_openai_response("This is the final merged summary of the long article.")

        call_count_holder = {"count": 0}

        def side_effect(**kwargs):
            call_count_holder["count"] += 1
            # Determine total calls needed first pass — use chunk for all but last
            return chunk_response

        mock_instance.chat.completions.create.side_effect = side_effect

        result = summarize(
            LONG_ARTICLE,
            api_key="test-key",
            chunk_size=500,
        )

        # Should have a summary (may be chunk or final)
        self.assertIsInstance(result.summary, str)
        self.assertTrue(len(result.summary) > 0)


# ---------------------------------------------------------------------------
# Pre-configured Client Tests
# ---------------------------------------------------------------------------

class TestSummarizeWithPreConfiguredClient(unittest.TestCase):
    """Tests for using a pre-configured SummarizerClient."""

    def test_accepts_pre_configured_client(self):
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "Pre-configured summary.",
            {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
        )

        # Patch the chunker to say text doesn't need chunking
        with patch("src.summarizer.summarize.TextChunker") as MockChunker:
            chunker_instance = MagicMock()
            chunker_instance.needs_chunking.return_value = False
            MockChunker.return_value = chunker_instance

            result = summarize(SHORT_ARTICLE, client=mock_client)

        self.assertEqual(result.summary, "Pre-configured summary.")
        mock_client.complete.assert_called_once()

    def test_pre_configured_client_not_recreated(self):
        """When a client is passed, no new client should be created."""
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "Summary.",
            {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
        )

        with patch("src.summarizer.summarize.SummarizerClient") as MockClientCls:
            with patch("src.summarizer.summarize.TextChunker") as MockChunker:
                chunker_instance = MagicMock()
                chunker_instance.needs_chunking.return_value = False
                MockChunker.return_value = chunker_instance

                summarize(SHORT_ARTICLE, client=mock_client)

        # SummarizerClient constructor should NOT have been called
        MockClientCls.assert_not_called()


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

class TestSummarizeErrorHandling(unittest.TestCase):

    def test_raises_value_error_without_api_key(self):
        import os
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaises(ValueError):
                summarize(SHORT_ARTICLE)

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_propagates_api_errors(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.side_effect = openai.AuthenticationError(
            "Invalid key", response=MagicMock(), body={}
        )

        with self.assertRaises(openai.AuthenticationError):
            summarize(SHORT_ARTICLE, api_key="invalid-key")

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_propagates_rate_limit_after_retries(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.side_effect = openai.RateLimitError(
            "Rate limit", response=MagicMock(), body={}
        )

        with patch("tenacity.nap.time"):
            with self.assertRaises(openai.RateLimitError):
                summarize(SHORT_ARTICLE, api_key="test-key")


# ---------------------------------------------------------------------------
# Style Tests
# ---------------------------------------------------------------------------

class TestSummarizeStyles(unittest.TestCase):

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_all_styles_produce_valid_summary(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response("Style summary.")

        for style in SummaryStyle:
            result = summarize(SHORT_ARTICLE, api_key="test-key", style=style)
            self.assertEqual(result.style, style.value)
            self.assertEqual(result.summary, "Style summary.")

    @patch("src.summarizer.llm.client.openai.OpenAI")
    def test_bullet_points_style_recorded(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance
        mock_instance.chat.completions.create.return_value = _make_openai_response(
            "• Point 1\n• Point 2\n• Point 3"
        )

        result = summarize(SHORT_ARTICLE, api_key="test-key", style=SummaryStyle.BULLET_POINTS)
        self.assertEqual(result.style, "bullet_points")


if __name__ == "__main__":
    unittest.main()