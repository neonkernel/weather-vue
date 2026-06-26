"""Tests for the Formatter class."""

import json
from datetime import datetime

import pytest

from src.summarizer.formatter import Formatter
from src.summarizer.models import Summary
from src.summarizer.styles import OutputFormat, SummaryStyle


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_summary():
    """A fully-populated Summary fixture."""
    return Summary(
        body="This is the summary body. It contains important information about the topic.",
        title="Test Article Title",
        source_url="https://example.com/test-article",
        model="gpt-4o",
        style=SummaryStyle.BRIEF.value,
        created_at=datetime(2026, 6, 26, 12, 0, 0),
    )


@pytest.fixture
def minimal_summary():
    """A Summary with only the required body field."""
    return Summary(body="Minimal summary body.")


@pytest.fixture
def bullet_summary():
    """A Summary with bullet-point body content."""
    return Summary(
        body="- Point one\n- Point two\n- Point three",
        title="Bullet Summary",
        source_url="https://example.com/bullets",
        model="claude-3",
        style=SummaryStyle.BULLETS.value,
    )


@pytest.fixture
def formatter():
    return Formatter()


# ---------------------------------------------------------------------------
# Plain text format tests
# ---------------------------------------------------------------------------

class TestTextFormat:
    def test_body_in_output(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert sample_summary.body in result

    def test_title_in_output(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert sample_summary.title in result

    def test_source_url_in_output(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert sample_summary.source_url in result

    def test_model_in_output(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert sample_summary.model in result

    def test_word_count_in_output(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert str(sample_summary.word_count) in result

    def test_minimal_summary_text(self, formatter, minimal_summary):
        result = formatter.format(minimal_summary, OutputFormat.TEXT)
        assert minimal_summary.body in result

    def test_returns_string(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert isinstance(result, str)

    def test_no_markdown_headers(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        # Plain text should not have Markdown headers
        assert "##" not in result


# ---------------------------------------------------------------------------
# Markdown format tests
# ---------------------------------------------------------------------------

class TestMarkdownFormat:
    def test_returns_string(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert isinstance(result, str)

    def test_has_title_h1_header(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert f"# {sample_summary.title}" in result

    def test_has_metadata_section(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert "## Metadata" in result

    def test_has_summary_section(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert "## Summary" in result

    def test_body_in_markdown(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert sample_summary.body in result

    def test_source_url_in_markdown(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert sample_summary.source_url in result

    def test_model_in_markdown(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert sample_summary.model in result

    def test_word_count_in_markdown(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert str(sample_summary.word_count) in result

    def test_markdown_link_format(self, formatter, sample_summary):
        """Source URL should be formatted as a Markdown link."""
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert f"[{sample_summary.source_url}]({sample_summary.source_url})" in result

    def test_model_in_code_span(self, formatter, sample_summary):
        """Model name should be in a code span in Markdown."""
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert f"`{sample_summary.model}`" in result

    def test_minimal_summary_markdown(self, formatter, minimal_summary):
        result = formatter.format(minimal_summary, OutputFormat.MARKDOWN)
        assert "# Summary" in result
        assert minimal_summary.body in result

    def test_structure_order(self, formatter, sample_summary):
        """Title should appear before metadata, metadata before summary."""
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        title_pos = result.index(f"# {sample_summary.title}")
        metadata_pos = result.index("## Metadata")
        summary_pos = result.index("## Summary")
        assert title_pos < metadata_pos < summary_pos


# ---------------------------------------------------------------------------
# JSON format tests
# ---------------------------------------------------------------------------

class TestJSONFormat:
    def test_returns_valid_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_body_in_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["body"] == sample_summary.body

    def test_title_in_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["title"] == sample_summary.title

    def test_source_url_in_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["source_url"] == sample_summary.source_url

    def test_model_in_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["model"] == sample_summary.model

    def test_word_count_in_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["word_count"] == sample_summary.word_count

    def test_style_in_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["style"] == sample_summary.style

    def test_created_at_in_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert "created_at" in parsed
        assert parsed["created_at"] is not None

    def test_json_schema_completeness(self, formatter, sample_summary):
        """JSON output should contain all expected top-level keys."""
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        expected_keys = {"body", "title", "source_url", "model", "word_count", "style", "created_at"}
        assert expected_keys.issubset(set(parsed.keys()))

    def test_minimal_summary_json(self, formatter, minimal_summary):
        result = formatter.format(minimal_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["body"] == minimal_summary.body

    def test_json_is_pretty_printed(self, formatter, sample_summary):
        """JSON output should be indented (pretty-printed)."""
        result = formatter.format(sample_summary, OutputFormat.JSON)
        assert "\n" in result
        assert "  " in result

    def test_bullet_summary_json(self, formatter, bullet_summary):
        result = formatter.format(bullet_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["body"] == bullet_summary.body
        assert parsed["style"] == SummaryStyle.BULLETS.value


# ---------------------------------------------------------------------------
# Unsupported format test
# ---------------------------------------------------------------------------

class TestInvalidFormat:
    def test_unsupported_format_raises(self, formatter, sample_summary):
        with pytest.raises((ValueError, AttributeError)):
            formatter.format(sample_summary, "xml")  # type: ignore


# ---------------------------------------------------------------------------
# Cross-format consistency tests
# ---------------------------------------------------------------------------

class TestCrossFormat:
    def test_body_present_in_all_formats(self, formatter, sample_summary):
        for fmt in OutputFormat:
            result = formatter.format(sample_summary, fmt)
            assert sample_summary.body in result, (
                f"Body not found in {fmt.value} output"
            )

    def test_formats_produce_different_output(self, formatter, sample_summary):
        outputs = {fmt: formatter.format(sample_summary, fmt) for fmt in OutputFormat}
        output_list = list(outputs.values())
        for i in range(len(output_list)):
            for j in range(i + 1, len(output_list)):
                assert output_list[i] != output_list[j], (
                    "Two different formats produced identical output"
                )