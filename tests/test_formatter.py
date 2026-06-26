"""Tests for the Formatter class."""

import json
from datetime import datetime

import pytest

from src.summarizer.formatter import Formatter
from src.summarizer.models import Summary
from src.summarizer.styles import OutputFormat


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_summary() -> Summary:
    """A fully-populated Summary instance for use in tests."""
    return Summary(
        content="Scientists discovered a new species of deep-sea fish that produces its own light.",
        title="New Bioluminescent Fish Discovered",
        source_url="https://example.com/fish-discovery",
        model="gpt-4o",
        word_count=14,
        style="brief",
        created_at=datetime(2026, 6, 26, 12, 0, 0),
    )


@pytest.fixture
def minimal_summary() -> Summary:
    """A Summary with only the required `content` field set."""
    return Summary(content="Short summary with no metadata.")


@pytest.fixture
def formatter() -> Formatter:
    return Formatter()


# ---------------------------------------------------------------------------
# Plain-text format
# ---------------------------------------------------------------------------

class TestTextFormat:
    def test_content_present(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert sample_summary.content in result

    def test_title_present(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert sample_summary.title in result

    def test_source_url_present(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert sample_summary.source_url in result

    def test_model_present(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert sample_summary.model in result

    def test_word_count_present(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert str(sample_summary.word_count) in result

    def test_minimal_summary_text(self, formatter, minimal_summary):
        """Minimal summary without metadata should still render cleanly."""
        result = formatter.format(minimal_summary, OutputFormat.TEXT)
        assert minimal_summary.content in result

    def test_returns_string(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.TEXT)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Markdown format
# ---------------------------------------------------------------------------

class TestMarkdownFormat:
    def test_h1_title_header(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert f"# {sample_summary.title}" in result

    def test_metadata_section_header(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert "## Metadata" in result

    def test_summary_section_header(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert "## Summary" in result

    def test_source_url_in_metadata(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert sample_summary.source_url in result

    def test_model_in_metadata(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert sample_summary.model in result

    def test_word_count_in_metadata(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert str(sample_summary.word_count) in result

    def test_content_in_body(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert sample_summary.content in result

    def test_metadata_uses_bold_labels(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert "**Source:**" in result or "**Model:**" in result

    def test_minimal_summary_uses_default_title(self, formatter, minimal_summary):
        """When no title is set, 'Summary' should be used as the H1."""
        result = formatter.format(minimal_summary, OutputFormat.MARKDOWN)
        assert "# Summary" in result

    def test_minimal_summary_has_no_metadata_section(self, formatter, minimal_summary):
        """A summary without metadata fields should not produce a Metadata section."""
        # Override created_at to None so metadata block is empty
        minimal_summary.created_at = None
        result = formatter.format(minimal_summary, OutputFormat.MARKDOWN)
        assert "## Metadata" not in result

    def test_sections_in_order(self, formatter, sample_summary):
        """Title → Metadata → Summary order must be maintained."""
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        title_pos = result.index(f"# {sample_summary.title}")
        metadata_pos = result.index("## Metadata")
        summary_pos = result.index("## Summary")
        assert title_pos < metadata_pos < summary_pos

    def test_returns_string(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.MARKDOWN)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# JSON format
# ---------------------------------------------------------------------------

class TestJsonFormat:
    def test_valid_json(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_content_field(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["content"] == sample_summary.content

    def test_title_field(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["title"] == sample_summary.title

    def test_source_url_field(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["source_url"] == sample_summary.source_url

    def test_model_field(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["model"] == sample_summary.model

    def test_word_count_field(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["word_count"] == sample_summary.word_count

    def test_style_field(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["style"] == sample_summary.style

    def test_created_at_field_is_string(self, formatter, sample_summary):
        """created_at should be serialized to a string (ISO format)."""
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert isinstance(parsed["created_at"], str)
        assert "2026" in parsed["created_at"]

    def test_json_schema_has_all_keys(self, formatter, sample_summary):
        """The JSON output must contain all Summary dataclass fields."""
        expected_keys = {"content", "title", "source_url", "model", "word_count", "style", "created_at"}
        result = formatter.format(sample_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert expected_keys.issubset(parsed.keys())

    def test_minimal_summary_json(self, formatter, minimal_summary):
        result = formatter.format(minimal_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["content"] == minimal_summary.content
        assert parsed["title"] is None

    def test_returns_string(self, formatter, sample_summary):
        result = formatter.format(sample_summary, OutputFormat.JSON)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Invalid format
# ---------------------------------------------------------------------------

class TestInvalidFormat:
    def test_raises_for_unknown_format(self, formatter, sample_summary):
        with pytest.raises(ValueError, match="Unsupported output format"):
            formatter.format(sample_summary, "xml")  # type: ignore[arg-type]