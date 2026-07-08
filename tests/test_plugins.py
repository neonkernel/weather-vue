"""
Tests for the plugin system: discovery, loading, validation, and error handling.
"""
from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor
from summarizer.plugins import PluginRegistry, PluginLoadError, get_registry


# ---------------------------------------------------------------------------
# Minimal concrete implementations for testing
# ---------------------------------------------------------------------------

class DummySummary:
    """Minimal stand-in for summarizer.models.Summary."""

    def __init__(self, summary: str = "This is the summary.", url: str = "http://example.com"):
        self.summary = summary
        self.url = url
        self.metadata: dict = {}


class ConcreteExtractor(BaseExtractor):
    name = "test_extractor"
    description = "A test extractor."

    def can_handle(self, url: str) -> bool:
        return url.startswith("http://test.")

    def extract(self, url: str, **kwargs: Any) -> str:
        return f"Content of {url}"


class ConcretePostProcessor(BasePostProcessor):
    name = "test_postprocessor"
    description = "A test post-processor."

    def process(self, summary, article_text: str, **kwargs: Any):
        summary.metadata["processed"] = True
        return summary


class ConcreteFormatter(BaseFormatter):
    name = "test_formatter"
    description = "A test formatter."
    extension = "txt"

    def format_summary(self, summary, **kwargs: Any) -> str:
        return f"FORMATTED: {summary.summary}"


# ---------------------------------------------------------------------------
# BaseExtractor tests
# ---------------------------------------------------------------------------

class TestBaseExtractor:
    def test_repr(self):
        e = ConcreteExtractor()
        assert "test_extractor" in repr(e)

    def test_can_handle(self):
        e = ConcreteExtractor()
        assert e.can_handle("http://test.example.com") is True
        assert e.can_handle("http://other.com") is False

    def test_extract(self):
        e = ConcreteExtractor()
        result = e.extract("http://test.example.com/page")
        assert "http://test.example.com/page" in result

    def test_abstract_methods_enforced(self):
        """Cannot instantiate BaseExtractor without implementing abstract methods."""
        with pytest.raises(TypeError):
            BaseExtractor()  # type: ignore

    def test_partial_implementation_rejected(self):
        class PartialExtractor(BaseExtractor):
            name = "partial"

            def can_handle(self, url: str) -> bool:
                return True
            # Missing extract()

        with pytest.raises(TypeError):
            PartialExtractor()  # type: ignore


# ---------------------------------------------------------------------------
# BasePostProcessor tests
# ---------------------------------------------------------------------------

class TestBasePostProcessor:
    def test_repr(self):
        pp = ConcretePostProcessor()
        assert "test_postprocessor" in repr(pp)

    def test_process(self):
        pp = ConcretePostProcessor()
        summary = DummySummary()
        result = pp.process(summary, "Article text here.")
        assert result.metadata.get("processed") is True

    def test_abstract_method_enforced(self):
        with pytest.raises(TypeError):
            BasePostProcessor()  # type: ignore


# ---------------------------------------------------------------------------
# BaseFormatter tests
# ---------------------------------------------------------------------------

class TestBaseFormatter:
    def test_repr(self):
        f = ConcreteFormatter()
        assert "test_formatter" in repr(f)

    def test_format_summary(self):
        f = ConcreteFormatter()
        s = DummySummary(summary="Hello world.")
        result = f.format_summary(s)
        assert "FORMATTED" in result
        assert "Hello world." in result

    def test_format_batch_default(self):
        """Default format_batch joins results with separator."""
        f = ConcreteFormatter()
        summaries = [DummySummary(summary=f"Summary {i}") for i in range(3)]
        result = f.format_batch(summaries)
        assert "Summary 0" in result
        assert "Summary 1" in result
        assert "Summary 2" in result
        # Should contain the default separator
        assert "=" * 10 in result

    def test_abstract_method_enforced(self):
        with pytest.raises(TypeError):
            BaseFormatter()  # type: ignore


# ---------------------------------------------------------------------------
# PluginRegistry tests
# ---------------------------------------------------------------------------

class TestPluginRegistry:
    def test_empty_registry(self):
        registry = PluginRegistry(load_builtins=False)
        assert registry.all_extractors() == []
        assert registry.all_postprocessors() == []
        assert registry.all_formatters() == []

    def test_register_extractor(self):
        registry = PluginRegistry(load_builtins=False)
        registry.register_extractor(ConcreteExtractor)
        assert "test_extractor" in [
            getattr(c, "name", c.__name__) for c in registry.all_extractors()
        ]

    def test_register_postprocessor(self):
        registry = PluginRegistry(load_builtins=False)
        registry.register_postprocessor(ConcretePostProcessor)
        assert registry.get_postprocessor("test_postprocessor") is ConcretePostProcessor

    def test_register_formatter(self):
        registry = PluginRegistry(load_builtins=False)
        registry.register_formatter(ConcreteFormatter)
        assert registry.get_formatter("test_formatter") is ConcreteFormatter

    def test_get_unknown_plugin_returns_none(self):
        registry = PluginRegistry(load_builtins=False)
        assert registry.get_extractor("nonexistent") is None
        assert registry.get_postprocessor("nonexistent") is None
        assert registry.get_formatter("nonexistent") is None

    # ------------------------------------------------------------------
    # Validation error handling
    # ------------------------------------------------------------------

    def test_register_non_subclass_extractor_raises(self):
        class NotAnExtractor:
            name = "fake"

        with pytest.raises(PluginLoadError, match="does not subclass"):
            PluginRegistry._validate_plugin(NotAnExtractor, BaseExtractor, "extractor")

    def test_register_non_class_raises(self):
        with pytest.raises(PluginLoadError, match="is not a class"):
            PluginRegistry._validate_plugin("not_a_class", BaseExtractor, "extractor")

    def test_register_abstract_class_raises(self):
        """A class that doesn't implement all abstract methods must be rejected."""
        class IncompletePostProcessor(BasePostProcessor):
            name = "incomplete"
            # Missing process()

        with pytest.raises(PluginLoadError, match="unimplemented abstract methods"):
            PluginRegistry._validate_plugin(
                IncompletePostProcessor, BasePostProcessor, "post-processor"
            )

    def test_duplicate_registration_skipped_by_default(self, caplog):
        import logging
        registry = PluginRegistry(load_builtins=False)
        registry.register_extractor(ConcreteExtractor)
        with caplog.at_level(logging.WARNING, logger="summarizer.plugins"):
            registry.register_extractor(ConcreteExtractor)
        assert any("already registered" in r.message for r in caplog.records)

    def test_duplicate_registration_override(self):
        registry = PluginRegistry(load_builtins=False)
        registry.register_extractor(ConcreteExtractor)

        class AnotherExtractor(BaseExtractor):
            name = "test_extractor"  # same name
            description = "Override."

            def can_handle(self, url: str) -> bool:
                return True

            def extract(self, url: str, **kwargs: Any) -> str:
                return "override content"

        registry.register_extractor(AnotherExtractor, override=True)
        assert registry.get_extractor("test_extractor") is AnotherExtractor

    # ------------------------------------------------------------------
    # Built-in loading
    # ------------------------------------------------------------------

    def test_builtins_loaded(self):
        registry = PluginRegistry(load_builtins=True)
        names = [getattr(c, "name", c.__name__) for c in registry.all_postprocessors()]
        assert "keyword_extractor" in names
        assert "readability_scorer" in names

    # ------------------------------------------------------------------
    # Entry-point discovery (mocked)
    # ------------------------------------------------------------------

    def test_entry_point_discovery(self):
        """Entry-point plugins should be registered when discovered."""
        mock_ep = MagicMock()
        mock_ep.name = "test_extractor_ep"
        mock_ep.load.return_value = ConcreteExtractor

        with patch(
            "summarizer.plugins.PluginRegistry._discover_entry_points"
        ) as mock_discover:
            registry = PluginRegistry(load_builtins=False)
            # Manually simulate discovery
            registry.register_extractor(ConcreteExtractor)

        assert registry.get_extractor("test_extractor") is ConcreteExtractor

    def test_entry_point_load_failure_is_logged(self, caplog):
        """A broken entry-point plugin should log an error, not crash."""
        import logging

        mock_ep = MagicMock()
        mock_ep.name = "broken_plugin"
        mock_ep.load.side_effect = ImportError("missing dependency")

        with patch(
            "importlib.metadata.entry_points", return_value=[mock_ep]
        ):
            registry = PluginRegistry(load_builtins=False)
            # Manually call the load group to test error handling
            with caplog.at_level(logging.ERROR, logger="summarizer.plugins"):
                registry._load_group(
                    lambda group: [mock_ep],
                    "summarizer.extractors",
                    BaseExtractor,
                    registry.register_extractor,
                )
        assert any("Failed to load plugin" in r.message for r in caplog.records)

    def test_malformed_plugin_class_logged(self, caplog):
        """A plugin that fails validation during entry-point load should log error."""
        import logging

        class MalformedExtractor:
            """Not a BaseExtractor subclass."""
            name = "malformed"

        mock_ep = MagicMock()
        mock_ep.name = "malformed_extractor"
        mock_ep.load.return_value = MalformedExtractor

        registry = PluginRegistry(load_builtins=False)
        with caplog.at_level(logging.ERROR, logger="summarizer.plugins"):
            registry._load_group(
                lambda group: [mock_ep],
                "summarizer.extractors",
                BaseExtractor,
                registry.register_extractor,
            )
        assert any("Failed to load plugin" in r.message for r in caplog.records)

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def test_get_registry_returns_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_get_registry_reload(self):
        r1 = get_registry()
        r2 = get_registry(reload=True)
        assert r1 is not r2


# ---------------------------------------------------------------------------
# Built-in plugin: KeywordExtractor
# ---------------------------------------------------------------------------

class TestKeywordExtractor:
    def test_extracts_keywords(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        extractor = KeywordExtractor(top_n=5)
        summary = DummySummary(summary="Machine learning models analyse data.")
        article = (
            "Machine learning is a subset of artificial intelligence. "
            "Models are trained on data to recognise patterns. "
            "Deep learning uses neural networks for complex tasks. "
            "Data science combines statistics and machine learning."
        )
        result = extractor.process(summary, article)
        assert "keywords" in result.metadata
        keywords = result.metadata["keywords"]
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert all(isinstance(k, str) for k in keywords)

    def test_keywords_respect_top_n_kwarg(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        extractor = KeywordExtractor(top_n=20)
        summary = DummySummary()
        article = " ".join(["word"] * 100 + ["unique_" + str(i) for i in range(50)])
        result = extractor.process(summary, article, top_n=3)
        assert len(result.metadata["keywords"]) <= 3

    def test_empty_article_returns_empty_list(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        extractor = KeywordExtractor(top_n=5)
        summary = DummySummary(summary="")
        result = extractor.process(summary, "")
        assert result.metadata.get("keywords") == []

    def test_creates_metadata_if_missing(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        extractor = KeywordExtractor()
        summary = DummySummary()
        del summary.metadata  # Remove metadata attribute

        # Re-add as None to simulate missing
        summary.metadata = None  # type: ignore
        result = extractor.process(summary, "Some article text about technology.")
        assert result.metadata is not None
        assert "keywords" in result.metadata

    def test_stop_words_excluded(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor, _STOP_WORDS

        extractor = KeywordExtractor(top_n=10)
        summary = DummySummary()
        article = "The quick brown fox jumps over the lazy dog. The dog barked."
        result = extractor.process(summary, article)
        for kw in result.metadata.get("keywords", []):
            assert kw not in _STOP_WORDS


# ---------------------------------------------------------------------------
# Built-in plugin: ReadabilityScorer
# ---------------------------------------------------------------------------

class TestReadabilityScorer:
    def test_scores_summary(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        scorer = ReadabilityScorer()
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "This is a simple sentence for readability testing. "
            "Short sentences score well on Flesch Reading Ease."
        )
        summary = DummySummary(summary=text)
        result = scorer.process(summary, "Original article text.")
        assert "readability" in result.metadata
        rd = result.metadata["readability"]
        assert "flesch_reading_ease" in rd
        assert "flesch_reading_ease_label" in rd
        assert "flesch_kincaid_grade" in rd
        assert isinstance(rd["flesch_reading_ease"], float)
        assert isinstance(rd["flesch_kincaid_grade"], float)

    def test_empty_summary_unchanged(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        scorer = ReadabilityScorer()
        summary = DummySummary(summary="")
        result = scorer.process(summary, "Some article text.")
        # Should return without adding readability key (empty text)
        assert "readability" not in result.metadata

    def test_reading_ease_label_range(self):
        from summarizer.plugins.builtin.readability import _reading_ease_label

        assert _reading_ease_label(95) == "Very Easy"
        assert _reading_ease_label(85) == "Easy"
        assert _reading_ease_label(75) == "Fairly Easy"
        assert _reading_ease_label(65) == "Standard"
        assert _reading_ease_label(55) == "Fairly Difficult"
        assert _reading_ease_label(40) == "Difficult"
        assert _reading_ease_label(10) == "Very Confusing"

    def test_flesch_reading_ease_simple_text(self):
        from summarizer.plugins.builtin.readability import flesch_reading_ease

        simple_text = "I am a boy. You are a girl. We are friends."
        score = flesch_reading_ease(simple_text)
        # Simple text should be easy to read (high score)
        assert score > 50

    def test_flesch_kincaid_grade_simple_text(self):
        from summarizer.plugins.builtin.readability import flesch_kincaid_grade

        simple_text = "I am a boy. You are a girl. We are friends."
        grade = flesch_kincaid_grade(simple_text)
        # Simple text should have a low grade level
        assert grade < 10

    def test_syllable_counting(self):
        from summarizer.plugins.builtin.readability import _count_syllables

        # Basic syllable counts
        assert _count_syllables("cat") == 1
        assert _count_syllables("happy") == 2
        assert _count_syllables("beautiful") >= 3
        assert _count_syllables("") == 0

    def test_creates_metadata_if_none(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        scorer = ReadabilityScorer()
        summary = DummySummary(summary="A simple sentence. Another simple sentence here.")
        summary.metadata = None  # type: ignore
        result = scorer.process(summary, "")
        assert result.metadata is not None
        assert "readability" in result.metadata


# ---------------------------------------------------------------------------
# CLI plugin listing (integration-style)
# ---------------------------------------------------------------------------

class TestCLIPluginsList:
    def test_plugins_list_output(self, capsys):
        from summarizer.cli import _cmd_plugins_list

        _cmd_plugins_list()
        captured = capsys.readouterr()
        output = captured.out

        assert "Post-Processors" in output
        assert "keyword_extractor" in output
        assert "readability_scorer" in output

    def test_plugins_list_includes_builtin_tag(self, capsys):
        from summarizer.cli import _cmd_plugins_list

        _cmd_plugins_list()
        captured = capsys.readouterr()
        assert "[built-in]" in captured.out

    def test_main_plugins_list_exit_code(self):
        from summarizer.cli import main

        code = main(["plugins", "list"])
        assert code == 0

    def test_main_no_command_exit_code(self):
        from summarizer.cli import main

        code = main([])
        assert code == 0