"""Integration-style tests for the summarize() pipeline using mocked LLM responses."""

from unittest.mock import MagicMock, patch, call
import pytest

from src.summarizer.summarize import summarize, _direct_summarize, _chunked_summarize
from src.summarizer.models import Article, Summary
from src.summarizer.llm.client import SummarizerClient
from src.summarizer.llm.prompts import PromptBuilder
from src.summarizer.exceptions import SummarizationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_mock_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    """Create a mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    mock_response.usage.prompt_tokens = prompt_tokens
    mock_response.usage.completion_tokens = completion_tokens
    mock_response.usage.total_tokens = prompt_tokens + completion_tokens
    return mock_response


@pytest.fixture
def mock_openai_client():
    """Patch the OpenAI client constructor."""
    with patch("src.summarizer.llm.client.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def summarizer_client(mock_openai_client):
    """Create a SummarizerClient backed by a mock OpenAI instance."""
    client = SummarizerClient(api_key="test-key", model="gpt-4o-mini")
    return client


@pytest.fixture
def short_article():
    return Article(
        content="Scientists have discovered a new species of deep-sea fish near the Mariana Trench. "
                "The fish, named Bathysaurus marianae, can survive at depths exceeding 8,000 meters. "
                "It has bioluminescent organs and a transparent body.",
        title="New Deep-Sea Fish Species Discovered",
        url="https://example.com/fish",
        author="Dr. Jane Smith",
    )


@pytest.fixture
def long_article():
    """Create an article long enough to trigger chunking."""
    content = " ".join([
        f"This is sentence number {i} of a very long article about climate change. "
        f"Researchers have found significant evidence that global temperatures are rising. "
        f"The impact on ecosystems is profound and far-reaching."
        for i in range(1000)
    ])
    return Article(
        content=content,
        title="Climate Change: A Comprehensive Analysis",
    )


# ---------------------------------------------------------------------------
# Direct summarization tests
# ---------------------------------------------------------------------------

class TestDirectSummarize:
    def test_returns_summary_object(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            "A new deep-sea fish species was discovered near the Mariana Trench."
        )
        result = summarize(short_article, client=summarizer_client)
        assert isinstance(result, Summary)

    def test_summary_text_matches_api_response(self, summarizer_client, mock_openai_client, short_article):
        expected = "A new deep-sea fish species was discovered near the Mariana Trench."
        mock_openai_client.chat.completions.create.return_value = make_mock_response(expected)
        result = summarize(short_article, client=summarizer_client)
        assert result.summary_text == expected

    def test_summary_has_correct_model(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        result = summarize(short_article, client=summarizer_client, model="gpt-4o-mini")
        assert result.model == "gpt-4o-mini"

    def test_summary_has_correct_style(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        result = summarize(short_article, client=summarizer_client, style="detailed")
        assert result.style == "detailed"

    def test_summary_method_is_direct_for_short_article(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        result = summarize(short_article, client=summarizer_client)
        assert result.method == "direct"

    def test_summary_includes_token_counts(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            "Summary", prompt_tokens=200, completion_tokens=80
        )
        result = summarize(short_article, client=summarizer_client)
        assert result.input_tokens == 200
        assert result.output_tokens == 80

    def test_summary_includes_cost_estimate(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            "Summary", prompt_tokens=200, completion_tokens=80
        )
        result = summarize(short_article, client=summarizer_client)
        assert result.estimated_cost_usd > 0

    def test_summary_includes_article_title(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        result = summarize(short_article, client=summarizer_client)
        assert result.article_title == "New Deep-Sea Fish Species Discovered"

    def test_api_called_once_for_short_article(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        summarize(short_article, client=summarizer_client)
        assert mock_openai_client.chat.completions.create.call_count == 1

    def test_user_prompt_contains_article_content(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        summarize(short_article, client=summarizer_client)

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[0] if call_args.args else call_args.kwargs["messages"]
        user_message = next(m for m in messages if m["role"] == "user")
        assert "Mariana Trench" in user_message["content"]

    def test_creates_client_if_not_provided(self, mock_openai_client, short_article):
        """Should auto-create a SummarizerClient if none is provided."""
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        # Should not raise — creates its own client
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = summarize(short_article)
        assert isinstance(result, Summary)


# ---------------------------------------------------------------------------
# Style variations
# ---------------------------------------------------------------------------

class TestSummarizeStyles:
    @pytest.mark.parametrize("style", ["concise", "detailed", "bullet", "executive"])
    def test_all_styles_produce_summary(self, summarizer_client, mock_openai_client, short_article, style):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            f"Summary in {style} style."
        )
        result = summarize(short_article, client=summarizer_client, style=style)
        assert result.style == style
        assert result.summary_text == f"Summary in {style} style."

    def test_different_styles_use_different_system_prompts(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")

        system_prompts = []
        for style in ["concise", "detailed"]:
            summarize(short_article, client=summarizer_client, style=style)
            call_args = mock_openai_client.chat.completions.create.call_args
            messages = call_args.kwargs.get("messages", call_args.args[0] if call_args.args else [])
            system_msg = next(m for m in messages if m["role"] == "system")
            system_prompts.append(system_msg["content"])
            mock_openai_client.chat.completions.create.reset_mock()

        assert system_prompts[0] != system_prompts[1]


# ---------------------------------------------------------------------------
# Chunked (map-reduce) summarization tests
# ---------------------------------------------------------------------------

class TestChunkedSummarize:
    def test_long_article_uses_map_reduce(self, summarizer_client, mock_openai_client, long_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            "Final combined summary of climate change article."
        )
        result = summarize(long_article, client=summarizer_client)
        assert result.method == "map_reduce"

    def test_long_article_makes_multiple_api_calls(self, summarizer_client, mock_openai_client, long_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Chunk summary")
        summarize(long_article, client=summarizer_client)
        # Should have more than 1 call (map + reduce)
        assert mock_openai_client.chat.completions.create.call_count > 1

    def test_long_article_returns_summary_object(self, summarizer_client, mock_openai_client, long_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Final summary")
        result = summarize(long_article, client=summarizer_client)
        assert isinstance(result, Summary)

    def test_long_article_summary_text_is_non_empty(self, summarizer_client, mock_openai_client, long_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Final summary")
        result = summarize(long_article, client=summarizer_client)
        assert result.summary_text
        assert len(result.summary_text) > 0

    def test_chunked_summary_accumulates_token_usage(self, summarizer_client, mock_openai_client, long_article):
        mock_openai_client.chat.completions.create.return_value = make_mock_response(
            "Summary", prompt_tokens=100, completion_tokens=50
        )
        result = summarize(long_article, client=summarizer_client)
        call_count = mock_openai_client.chat.completions.create.call_count
        # Total tokens should be call_count * (100 + 50)
        assert result.input_tokens == call_count * 100
        assert result.output_tokens == call_count * 50


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestSummarizeErrors:
    def test_api_error_raises_summarization_error(self, summarizer_client, mock_openai_client, short_article):
        mock_openai_client.chat.completions.create.side_effect = Exception("Unexpected API error")
        with pytest.raises(SummarizationError):
            summarize(short_article, client=summarizer_client)

    def test_summarization_error_wraps_original(self, summarizer_client, mock_openai_client, short_article):
        original_error = Exception("Original error")
        mock_openai_client.chat.completions.create.side_effect = original_error
        with pytest.raises(SummarizationError) as exc_info:
            summarize(short_article, client=summarizer_client)
        assert exc_info.value.__cause__ is original_error

    def test_invalid_style_raises_value_error(self, summarizer_client, mock_openai_client, short_article):
        with pytest.raises(ValueError):
            summarize(short_article, client=summarizer_client, style="invalid_style")


# ---------------------------------------------------------------------------
# Article without title
# ---------------------------------------------------------------------------

class TestSummarizeWithoutTitle:
    def test_article_without_title(self, summarizer_client, mock_openai_client):
        article = Article(content="Some content without a title.")
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        result = summarize(article, client=summarizer_client)
        assert isinstance(result, Summary)
        assert result.article_title is None

    def test_article_without_title_still_sends_content(self, summarizer_client, mock_openai_client):
        article = Article(content="Unique article content XYZ123.")
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Summary")
        summarize(article, client=summarizer_client)

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages", [])
        all_content = " ".join(m["content"] for m in messages)
        assert "XYZ123" in all_content


# ---------------------------------------------------------------------------
# _direct_summarize and _chunked_summarize unit tests
# ---------------------------------------------------------------------------

class TestInternalHelpers:
    def test_direct_summarize_returns_string(self, summarizer_client, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Direct summary")
        builder = PromptBuilder(style="concise")
        result = _direct_summarize(
            article_text="Some article text.",
            article_title="Test Article",
            client=summarizer_client,
            prompt_builder=builder,
        )
        assert result == "Direct summary"

    def test_chunked_summarize_returns_string(self, summarizer_client, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = make_mock_response("Chunk summary")
        builder = PromptBuilder(style="concise")
        long_text = "word " * 500
        result = _chunked_summarize(
            article_text=long_text,
            article_title="Long Article",
            client=summarizer_client,
            prompt_builder=builder,
            model="gpt-4o-mini",
            chunk_overlap=10,
        )
        assert isinstance(result, str)
        assert len(result) > 0