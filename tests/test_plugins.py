"""
Tests for the summarizer plugin system.

Covers:
- PluginRegistry discovery and loading
- Built-in plugins (KeywordExtractor, ReadabilityScorer)
- BaseExtractor / BasePostProcessor / BaseFormatter ABCs
- Error handling for malformed plugins
- Manual registration
- CLI `plugins list` command
"""

from __future__ import annotations

import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure we can import without a full install
from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor
from summarizer.plugins import PluginRegistry, get_registry, reset_registry
from summarizer.plugins.builtin.keyword_extractor import (
    KeywordExtractor,
    _tokenize,
    _tf_idf_keywords,
    _count_syllables,
)
from summarizer.plugins.builtin.readability import (
    ReadabilityScorer,
    flesch_reading_ease,
    flesch_kincaid_grade,
    _count_syllables as rs_count_syllables,
    _split_sentences,
    _tokenize_words,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_global_registry():
    """Reset the global registry singleton before each test."""
    reset_registry()
    yield
    reset_registry()


class _ConcreteExtractor(BaseExtractor):
    name = "test_extractor"
    description = "A test extractor."

    def can_handle(self, url: str) -> bool:
        return url.startswith("https://test.")

    def extract(self, url: str, **kwargs: Any) -> dict:
        return {"text": f"Extracted text from {url}", "title": "Test Article"}


class _ConcretePostProcessor(BasePostProcessor):
    name = "test_postprocessor"
    description = "A test post-processor."
    enabled_by_default = True

    def process(self, summary: Any, article_text: str = "", **kwargs: Any) -> Any:
        if hasattr(summary, "metadata"):
            summary.metadata["test_processed"] = True
        return summary


class _ConcreteFormatter(BaseFormatter):
    name = "test_formatter"
    description = "A test formatter."
    extension = ".test"

    def format(self, summary: Any, **kwargs: Any) -> str:
        return f"FORMATTED: {getattr(summary, 'text', str(summary))}"


class _SimpleSummary:
    """Minimal summary object for testing."""

    def __init__(self, text: str = "Hello world. This is a test.") -> None:
        self.text = text
        self.metadata: dict = {}

    def __str__(self) -> str:
        return self.text


# ---------------------------------------------------------------------------
# Base ABC tests
# ---------------------------------------------------------------------------

class TestBaseABCs:
    def test_base_extractor_is_abstract(self):
        with pytest.raises(TypeError):
            BaseExtractor()

    def test_base_postprocessor_is_abstract(self):
        with pytest.raises(TypeError):
            BasePostProcessor()

    def test_base_formatter_is_abstract(self):
        with pytest.raises(TypeError):
            BaseFormatter()

    def test_concrete_extractor_instantiates(self):
        ext = _ConcreteExtractor()
        assert ext.name == "test_extractor"

    def test_concrete_postprocessor_instantiates(self):
        pp = _ConcretePostProcessor()
        assert pp.name == "test_postprocessor"
        assert pp.enabled_by_default is True

    def test_concrete_formatter_instantiates(self):
        fmt = _ConcreteFormatter()
        assert fmt.name == "test_formatter"
        assert fmt.extension == ".test"

    def test_extractor_repr(self):
        ext = _ConcreteExtractor()
        assert "test_extractor" in repr(ext)

    def test_postprocessor_repr(self):
        pp = _ConcretePostProcessor()
        assert "test_postprocessor" in repr(pp)

    def test_formatter_repr(self):
        fmt = _ConcreteFormatter()
        assert "test_formatter" in repr(fmt)


# ---------------------------------------------------------------------------
# PluginRegistry tests
# ---------------------------------------------------------------------------

class TestPluginRegistry:
    def test_registry_starts_empty(self):
        registry = PluginRegistry()
        assert registry.extractors == []
        assert registry.postprocessors == []
        assert registry.formatters == []

    def test_manual_register_extractor(self):
        registry = PluginRegistry()
        ext = _ConcreteExtractor()
        registry.register_extractor(ext)
        assert ext in registry.extractors

    def test_manual_register_postprocessor(self):
        registry = PluginRegistry()
        pp = _ConcretePostProcessor()
        registry.register_postprocessor(pp)
        assert pp in registry.postprocessors

    def test_manual_register_formatter(self):
        registry = PluginRegistry()
        fmt = _ConcreteFormatter()
        registry.register_formatter(fmt)
        assert fmt in registry.formatters

    def test_register_wrong_type_raises(self):
        registry = PluginRegistry()
        with pytest.raises(TypeError):
            registry.register_extractor("not_an_extractor")  # type: ignore
        with pytest.raises(TypeError):
            registry.register_postprocessor(42)  # type: ignore
        with pytest.raises(TypeError):
            registry.register_formatter(object())  # type: ignore

    def test_discover_loads_builtin_plugins(self):
        registry = PluginRegistry()
        registry.discover(include_builtin=True)
        names = [pp.name for pp in registry.postprocessors]
        assert "keyword_extractor" in names
        assert "readability_scorer" in names

    def test_discover_without_builtin_skips_them(self):
        registry = PluginRegistry()
        # Mock entry points to return nothing
        with patch("summarizer.plugins._load_entry_points", return_value=[]):
            registry.discover(include_builtin=False)
        assert registry.postprocessors == []

    def test_get_extractor_for_matching_url(self):
        registry = PluginRegistry()
        registry.register_extractor(_ConcreteExtractor())
        result = registry.get_extractor_for("https://test.example.com/article")
        assert result is not None
        assert result.name == "test_extractor"

    def test_get_extractor_for_non_matching_url(self):
        registry = PluginRegistry()
        registry.register_extractor(_ConcreteExtractor())
        result = registry.get_extractor_for("https://other.example.com/article")
        assert result is None

    def test_get_extractor_for_empty_registry(self):
        registry = PluginRegistry()
        assert registry.get_extractor_for("https://example.com") is None

    def test_apply_postprocessors_enabled_only(self):
        registry = PluginRegistry()
        pp = _ConcretePostProcessor()
        pp.enabled_by_default = True
        registry.register_postprocessor(pp)

        summary = _SimpleSummary()
        result = registry.apply_postprocessors(summary, enabled_only=True)
        assert result.metadata.get("test_processed") is True

    def test_apply_postprocessors_skips_disabled(self):
        registry = PluginRegistry()
        pp = _ConcretePostProcessor()
        pp.enabled_by_default = False
        registry.register_postprocessor(pp)

        summary = _SimpleSummary()
        result = registry.apply_postprocessors(summary, enabled_only=True)
        assert "test_processed" not in result.metadata

    def test_apply_postprocessors_all(self):
        registry = PluginRegistry()
        pp = _ConcretePostProcessor()
        pp.enabled_by_default = False
        registry.register_postprocessor(pp)

        summary = _SimpleSummary()
        result = registry.apply_postprocessors(summary, enabled_only=False)
        assert result.metadata.get("test_processed") is True

    def test_apply_postprocessors_handles_exception_gracefully(self):
        """A failing processor should not crash the whole pipeline."""

        class _BrokenProcessor(BasePostProcessor):
            name = "broken"
            enabled_by_default = True

            def process(self, summary, article_text="", **kwargs):
                raise RuntimeError("Intentional failure")

        registry = PluginRegistry()
        registry.register_postprocessor(_BrokenProcessor())

        summary = _SimpleSummary()
        # Should not raise
        result = registry.apply_postprocessors(summary, enabled_only=True)
        assert result is summary

    def test_summary_table_includes_all_plugin_types(self):
        registry = PluginRegistry()
        registry.register_extractor(_ConcreteExtractor())
        registry.register_postprocessor(_ConcretePostProcessor())
        registry.register_formatter(_ConcreteFormatter())

        table = registry.summary_table()
        types_found = {row["type"] for row in table}
        assert "extractor" in types_found
        assert "postprocessor" in types_found
        assert "formatter" in types_found

    def test_summary_table_empty_registry(self):
        registry = PluginRegistry()
        assert registry.summary_table() == []


# ---------------------------------------------------------------------------
# Global registry singleton tests
# ---------------------------------------------------------------------------

class TestGlobalRegistry:
    def test_get_registry_returns_singleton(self):
        r1 = get_registry(auto_discover=False)
        r2 = get_registry(auto_discover=False)
        assert r1 is r2

    def test_reset_registry_clears_singleton(self):
        r1 = get_registry(auto_discover=False)
        reset_registry()
        r2 = get_registry(auto_discover=False)
        assert r1 is not r2

    def test_get_registry_auto_discover(self):
        registry = get_registry(auto_discover=True)
        # Built-in post-processors should be loaded
        names = [pp.name for pp in registry.postprocessors]
        assert "keyword_extractor" in names


# ---------------------------------------------------------------------------
# Entry point loading & error handling
# ---------------------------------------------------------------------------

class TestEntryPointLoading:
    def test_malformed_class_is_skipped(self):
        """A class that doesn't subclass the correct ABC should be skipped."""
        registry = PluginRegistry()

        class NotAPostProcessor:
            pass

        result = registry._instantiate(NotAPostProcessor, BasePostProcessor)
        assert result is None

    def test_base_class_itself_is_skipped(self):
        result = PluginRegistry._instantiate(BasePostProcessor, BasePostProcessor)
        assert result is None

    def test_instantiation_error_is_skipped(self):
        class _BadInit(BasePostProcessor):
            name = "bad_init"

            def __init__(self):
                raise RuntimeError("Cannot instantiate")

            def process(self, summary, article_text="", **kwargs):
                return summary

        result = PluginRegistry._instantiate(_BadInit, BasePostProcessor)
        assert result is None

    def test_import_class_invalid_path_raises(self):
        with pytest.raises(ValueError, match="Expected 'module.path:ClassName'"):
            PluginRegistry._import_class("no_colon_here")

    def test_entry_point_load_failure_is_skipped(self):
        """A broken entry point should not crash the discovery process."""
        bad_ep = MagicMock()
        bad_ep.name = "bad_plugin"
        bad_ep.load.side_effect = ImportError("module not found")

        with patch("summarizer.plugins._load_entry_points", return_value=[bad_ep]):
            registry = PluginRegistry()
            registry.discover(include_builtin=False)

        # Registry should still be functional
        assert registry.postprocessors == []

    def test_extractor_can_handle_exception_is_caught(self):
        class _BrokenExtractor(BaseExtractor):
            name = "broken_extractor"

            def can_handle(self, url):
                raise RuntimeError("boom")

            def extract(self, url, **kwargs):
                return {"text": ""}

        registry = PluginRegistry()
        registry.register_extractor(_BrokenExtractor())
        # Should not raise
        result = registry.get_extractor_for("https://example.com")
        assert result is None


# ---------------------------------------------------------------------------
# KeywordExtractor tests
# ---------------------------------------------------------------------------

class TestKeywordExtractor:
    def test_name_and_description(self):
        ke = KeywordExtractor()
        assert ke.name == "keyword_extractor"
        assert "TF-IDF" in ke.description or "keyword" in ke.description.lower()

    def test_enabled_by_default(self):
        assert KeywordExtractor.enabled_by_default is True

    def test_extracts_keywords_into_metadata(self):
        ke = KeywordExtractor(top_n=5)
        summary = _SimpleSummary("A brief summary of the article.")
        article_text = (
            "Machine learning algorithms are powerful tools for data analysis. "
            "Neural networks and deep learning models have revolutionized computer vision. "
            "Data scientists use machine learning to build predictive models for business. "
            "Algorithms process large datasets to extract meaningful patterns and insights."
        )
        result = ke.process(summary, article_text=article_text)
        assert "keywords" in result.metadata
        assert isinstance(result.metadata["keywords"], list)
        assert len(result.metadata["keywords"]) <= 5

    def test_extracts_keywords_empty_text(self):
        ke = KeywordExtractor()
        summary = _SimpleSummary()
        result = ke.process(summary, article_text="")
        assert "keywords" in result.metadata
        assert result.metadata["keywords"] == []

    def test_top_n_kwarg_override(self):
        ke = KeywordExtractor(top_n=20)
        summary = _SimpleSummary()
        article_text = " ".join(["word" + str(i) for i in range(50)])
        result = ke.process(summary, article_text=article_text, top_n=3)
        assert len(result.metadata["keywords"]) <= 3

    def test_no_metadata_attribute_uses_setattr(self):
        ke = KeywordExtractor()

        class _NoMetaSummary:
            text = "test"

        s = _NoMetaSummary()
        result = ke.process(s, article_text="machine learning data science algorithms")
        assert hasattr(result, "keywords")

    def test_tokenize(self):
        tokens = _tokenize("Hello, World! This is a test.")
        assert "hello" in tokens
        assert "world" in tokens
        assert all(t.isalpha() for t in tokens)

    def test_tf_idf_returns_scored_list(self):
        tokens = _tokenize(
            "data science machine learning data data science python algorithms"
        )
        from summarizer.plugins.builtin.keyword_extractor import _BUILTIN_STOPWORDS

        results = _tf_idf_keywords(tokens, _BUILTIN_STOPWORDS, top_n=5)
        assert isinstance(results, list)
        assert all(isinstance(kw, str) and isinstance(score, float) for kw, score in results)

    def test_tf_idf_empty_tokens(self):
        results = _tf_idf_keywords([], frozenset(), top_n=5)
        assert results == []

    def test_stopwords_are_excluded(self):
        ke = KeywordExtractor(top_n=10)
        summary = _SimpleSummary()
        # Article with only stop words
        result = ke.process(summary, article_text="the and or but in on at to for of")
        assert result.metadata["keywords"] == []


# ---------------------------------------------------------------------------
# ReadabilityScorer tests
# ---------------------------------------------------------------------------

class TestReadabilityScorer:
    def test_name_and_description(self):
        rs = ReadabilityScorer()
        assert rs.name == "readability_scorer"
        assert "readability" in rs.description.lower() or "flesch" in rs.description.lower()

    def test_enabled_by_default(self):
        assert ReadabilityScorer.enabled_by_default is True

    def test_adds_readability_metadata(self):
        rs = ReadabilityScorer()
        summary = _SimpleSummary(
            "The quick brown fox jumps over the lazy dog. "
            "Scientists discovered a new species of deep-sea fish near hydrothermal vents."
        )
        result = rs.process(summary)
        assert "readability_score" in result.metadata
        assert "readability_label" in result.metadata
        assert "flesch_kincaid_grade" in result.metadata
        assert "readability_word_count" in result.metadata
        assert "readability_sentence_count" in result.metadata

    def test_readability_score_range(self):
        rs = ReadabilityScorer()
        # Very simple text should score high (easy)
        summary = _SimpleSummary("I like cats. Cats are fun. Dogs run fast.")
        rs.process(summary)
        score = summary.metadata["readability_score"]
        # Simple text should be reasonably readable
        assert isinstance(score, float)
        assert score > 0

    def test_empty_summary_skipped(self):
        rs = ReadabilityScorer()
        summary = _SimpleSummary("")
        result = rs.process(summary)
        # Metadata should remain empty
        assert result.metadata == {}

    def test_no_metadata_attribute_uses_setattr(self):
        rs = ReadabilityScorer()

        class _NoMetaSummary:
            text = "The quick brown fox. Simple and clear text here."

        s = _NoMetaSummary()
        result = rs.process(s)
        assert hasattr(result, "readability_score")

    def test_flesch_reading_ease_formula(self):
        # 100 words, 5 sentences, 150 syllables
        score = flesch_reading_ease(100, 5, 150)
        expected = 206.835 - 1.015 * (100 / 5) - 84.6 * (150 / 100)
        assert abs(score - expected) < 0.01

    def test_flesch_reading_ease_zero_division(self):
        assert flesch_reading_ease(0, 0, 0) == 0.0
        assert flesch_reading_ease(100, 0, 150) == 0.0

    def test_flesch_kincaid_grade_formula(self):
        grade = flesch_kincaid_grade(100, 5, 150)
        expected = 0.39 * (100 / 5) + 11.8 * (150 / 100) - 15.59
        assert abs(grade - expected) < 0.01

    def test_flesch_kincaid_grade_zero_division(self):
        assert flesch_kincaid_grade(0, 0, 0) == 0.0

    def test_count_syllables_basic(self):
        assert rs_count_syllables("cat") == 1
        assert rs_count_syllables("table") >= 1
        assert rs_count_syllables("beautiful") >= 3

    def test_count_syllables_empty(self):
        assert rs_count_syllables("") == 0

    def test_split_sentences(self):
        text = "Hello world. How are you? I am fine!"
        sentences = _split_sentences(text)
        assert len(sentences) == 3

    def test_tokenize_words(self):
        words = _tokenize_words("Hello, world! 123 test.")
        assert "Hello" in words
        assert "world" in words
        assert "123" not in words

    def test_get_text_tries_multiple_attributes(self):
        rs = ReadabilityScorer()

        class _SummaryWithContent:
            content = "Content attribute text. It has multiple sentences."
            metadata: dict = {}

        s = _SummaryWithContent()
        rs.process(s)
        assert "readability_score" in s.metadata

    def test_word_count_in_metadata(self):
        rs = ReadabilityScorer()
        text = "One two three four five. Six seven eight nine ten."
        summary = _SimpleSummary(text)
        rs.process(summary)
        assert summary.metadata["readability_word_count"] == 10


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestCLIPluginsList:
    def test_plugins_list_command(self, capsys):
        from summarizer.cli import main

        exit_code = main(["plugins", "list"])
        captured = capsys.readouterr()
        assert exit_code == 0
        # Should show at least the built-in post-processors
        assert "keyword_extractor" in captured.out or "postprocessor" in captured.out

    def test_plugins_list_shows_headers(self, capsys):
        from summarizer.cli import main

        main(["plugins", "list"])
        captured = capsys.readouterr()
        output = captured.out
        assert "TYPE" in output
        assert "NAME" in output

    def test_no_plugins_flag_skips_registry(self, capsys):
        """Ensure --no-plugins flag prevents registry usage."""
        from summarizer.cli import main

        # This tests the summarize command with no-plugins flag
        exit_code = main(["--no-plugins", "summarize", "https://example.com"])
        assert exit_code == 0

    def test_summarize_command_applies_postprocessors(self, capsys):
        from summarizer.cli import main

        exit_code = main(["summarize", "https://example.com"])
        captured = capsys.readouterr()
        assert exit_code == 0
        # Post-processors should have added metadata to the output
        output = captured.out
        assert "example.com" in output or "summary" in output.lower()

    def test_summarize_json_format(self, capsys):
        import json

        from summarizer.cli import main

        exit_code = main(["summarize", "--format", "json", "https://example.com"])
        captured = capsys.readouterr()
        assert exit_code == 0
        # Find JSON in output
        lines = captured.out.strip().split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith("{"):
                in_json = True
            if in_json:
                json_lines.append(line)
            if in_json and line.strip() == "}":
                break
        if json_lines:
            data = json.loads("\n".join(json_lines))
            assert "summary" in data

    def test_no_postprocess_flag(self, capsys):
        from summarizer.cli import main

        exit_code = main(["summarize", "--no-postprocess", "https://example.com"])
        assert exit_code == 0


# ---------------------------------------------------------------------------
# Concurrent/multiple registration tests
# ---------------------------------------------------------------------------

class TestMultipleRegistration:
    def test_multiple_postprocessors_applied_in_order(self):
        """Processors should be applied in registration order."""
        call_order = []

        class _Proc1(BasePostProcessor):
            name = "proc1"
            enabled_by_default = True

            def process(self, summary, article_text="", **kwargs):
                call_order.append(1)
                return summary

        class _Proc2(BasePostProcessor):
            name = "proc2"
            enabled_by_default = True

            def process(self, summary, article_text="", **kwargs):
                call_order.append(2)
                return summary

        registry = PluginRegistry()
        registry.register_postprocessor(_Proc1())
        registry.register_postprocessor(_Proc2())

        summary = _SimpleSummary()
        registry.apply_postprocessors(summary, enabled_only=True)
        assert call_order == [1, 2]

    def test_formatters_registry_selects_correct_formatter(self):
        registry = PluginRegistry()
        registry.register_formatter(_ConcreteFormatter())

        from summarizer.cli import _format_summary

        summary = _SimpleSummary("test text")
        result = _format_summary(summary, "test_formatter", registry)
        assert result.startswith("FORMATTED:")

    def test_unknown_format_falls_back_to_text(self):
        registry = PluginRegistry()

        from summarizer.cli import _format_summary

        summary = _SimpleSummary("hello world")
        result = _format_summary(summary, "unknown_format", registry)
        assert "hello world" in result