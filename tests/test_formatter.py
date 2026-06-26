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

FIXED_DT = datetime(2026, 6, 26, 12, 0, 0)


@pytest.fixture
def full_summary() -> Summary:
    """A Summary with all fields populated."""
    return Summary(
        body="This is the summary body. It explains the article concisely.",
        title="Breaking News: Major Discovery",
        source_url="https://example.com/article",
        model="gpt-4o",
        style="brief",
        word_count=None,  # will be auto-computed
        created_at=FIXED_DT,
    )


@pytest.fixture
def minimal_summary() -> Summary:
    """A Summary with only the required body field."""
    return Summary(
        body="Minimal body text.",
        title=None,
        source_url=None,
        model=None,
        style=None,
        word_count=None,
        created_at=None,
    )


@pytest.fixture
def formatter() -> Formatter:
    return Formatter()


# ---------------------------------------------------------------------------
# Plain text format
# ---------------------------------------------------------------------------

class TestTextFormat:
    def test_body_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.TEXT)
        assert full_summary.body in result

    def test_title_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.TEXT)
        assert full_summary.title in result

    def test_title_underline_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.TEXT)
        assert "=" * len(full_summary.title) in result

    def test_model_in_metadata(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.TEXT)
        assert full_summary.model in result

    def test_source_url_in_metadata(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.TEXT)
        assert full_summary.source_url in result

    def test_style_in_metadata(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.TEXT)
        assert full_summary.style in result

    def test_separator_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.TEXT)
        assert "---" in result

    def test_minimal_summary_no_crash(self, formatter, minimal_summary):
        result = formatter.format(minimal_summary, OutputFormat.TEXT)
        assert minimal_summary.body in result

    def test_word_count_computed(self, formatter, full_summary):
        # word_count=None triggers auto-computation in __post_init__
        assert full_summary.word_count is not None
        result = formatter.format(full_summary, OutputFormat.TEXT)
        assert str(full_summary.word_count) in result


# ---------------------------------------------------------------------------
# Markdown format
# ---------------------------------------------------------------------------

class TestMarkdownFormat:
    def test_h1_title_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert f"# {full_summary.title}" in result

    def test_summary_h2_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert "## Summary" in result

    def test_body_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert full_summary.body in result

    def test_metadata_table_has_source(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert full_summary.source_url in result

    def test_metadata_table_has_model(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert full_summary.model in result

    def test_metadata_table_has_word_count(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert str(full_summary.word_count) in result

    def test_metadata_table_header_separator(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert "|-------|-------|" in result

    def test_horizontal_rule_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert "---" in result

    def test_minimal_uses_default_title(self, formatter, minimal_summary):
        result = formatter.format(minimal_summary, OutputFormat.MARKDOWN)
        assert "# Summary" in result

    def test_datetime_formatted(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.MARKDOWN)
        assert "2026-06-26" in result


# ---------------------------------------------------------------------------
# JSON format
# ---------------------------------------------------------------------------

class TestJsonFormat:
    def test_valid_json(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_body_field_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert "body" in parsed
        assert parsed["body"] == full_summary.body

    def test_title_field_present(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["title"] == full_summary.title

    def test_source_url_field(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["source_url"] == full_summary.source_url

    def test_model_field(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["model"] == full_summary.model

    def test_style_field(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["style"] == full_summary.style

    def test_word_count_field(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert "word_count" in parsed
        assert isinstance(parsed["word_count"], int)

    def test_created_at_is_string(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert isinstance(parsed["created_at"], str)

    def test_created_at_iso_format(self, formatter, full_summary):
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(parsed["created_at"])
        assert dt.year == 2026

    def test_minimal_summary_valid_json(self, formatter, minimal_summary):
        result = formatter.format(minimal_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["body"] == minimal_summary.body

    def test_all_dataclass_fields_present(self, formatter, full_summary):
        """JSON output should contain every field from the Summary dataclass."""
        result = formatter.format(full_summary, OutputFormat.JSON)
        parsed = json.loads(result)
        expected_fields = {"body", "title", "source_url", "model", "style", "word_count", "created_at"}
        assert expected_fields.issubset(parsed.keys())


# ---------------------------------------------------------------------------
# Unsupported format
# ---------------------------------------------------------------------------

class TestUnsupportedFormat:
    def test_raises_value_error(self, formatter, full_summary):
        with pytest.raises((ValueError, AttributeError)):
            formatter.format(full_summary, "xml")  # type: ignore[arg-type]