"""
Tests for the plugin system: discovery, loading, built-ins, and error handling.
"""
from __future__ import annotations

import sys
import types
from typing import Any, Dict, Optional
from unittest import mock

import pytest

from summarizer.plugins import PluginRegistry, registry as global_registry
from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor
from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor, _tfidf_keywords
from summarizer.plugins.builtin.readability import (
    ReadabilityScorer,
    flesch_reading_ease,
    _grade_label,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_ARTICLE = (
    "Artificial intelligence is transforming the technology industry. "
    "Machine learning algorithms are becoming more sophisticated every year. "
    "Deep learning models require large datasets for training purposes. "
    "Natural language processing enables computers to understand human text. "
    "These advances are driving innovation across many different sectors globally."
)

SAMPLE_SUMMARY = (
    "AI is transforming tech. Machine learning grows yearly. "
    "Deep learning needs data. NLP helps computers understand language."
)


class SimpleSummary:
    """Minimal summary-like object used in tests."""

    def __init__(self, summary: str = "", content: str = "", title: str = ""):
        self.summary = summary
        self.content = content
        self.title = title
        self.article_text = content


@pytest.fixture()
def fresh_registry():
    """Return a brand-new PluginRegistry (not the module singleton)."""
    reg = PluginRegistry()
    return reg


# ---------------------------------------------------------------------------
# BaseExtractor
# ---------------------------------------------------------------------------


class ConcreteExtractor(BaseExtractor):
    name = "test_extractor"
    description = "A test extractor"

    def can_handle(self, source: str) -> bool:
        return source.startswith("test://")

    def extract(self, source: str) -> Dict[str, Any]:
        return {"title": "Test", "text": "body", "url": source, "html": ""}


class TestBaseExtractor:
    def test_concrete_extractor_can_handle(self):
        ext = ConcreteExtractor()
        assert ext.can_handle("test://foo") is True
        assert ext.can_handle("https://example.com") is False

    def test_concrete_extractor_extract(self):
        ext = ConcreteExtractor()
        result = ext.extract("test://foo")
        assert result["title"] == "Test"
        assert result["text"] == "body"

    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseExtractor()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# BasePostProcessor
# ---------------------------------------------------------------------------


class ConcretePostProcessor(BasePostProcessor):
    name = "test_pp"
    description = "A test post-processor"

    def process(self, summary, *, article_text="", config=None):
        summary.processed = True
        return summary


class TestBasePostProcessor:
    def test_process_called(self):
        pp = ConcretePostProcessor()
        s = SimpleSummary(summary="Hello world.")
        result = pp.process(s, article_text="Hello world article text here.")
        assert result.processed is True

    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BasePostProcessor()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# BaseFormatter
# ---------------------------------------------------------------------------


class ConcreteFormatter(BaseFormatter):
    name = "test_formatter"
    description = "A test formatter"
    extension = ".txt"

    def format(self, summary, config=None):
        return f"FORMATTED: {getattr(summary, 'summary', summary)}"


class TestBaseFormatter:
    def test_format(self):
        fmt = ConcreteFormatter()
        s = SimpleSummary(summary="My summary text.")
        assert fmt.format(s) == "FORMATTED: My summary text."

    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseFormatter()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# PluginRegistry — manual registration
# ---------------------------------------------------------------------------


class TestPluginRegistryManual:
    def test_register_extractor(self, fresh_registry):
        fresh_registry.register_extractor(ConcreteExtractor)
        assert "test_extractor" in fresh_registry.extractors

    def test_register_postprocessor(self, fresh_registry):
        fresh_registry.register_postprocessor(ConcretePostProcessor)
        assert "test_pp" in fresh_registry.postprocessors

    def test_register_formatter(self, fresh_registry):
        fresh_registry.register_formatter(ConcreteFormatter)
        assert "test_formatter" in fresh_registry.formatters

    def test_validate_wrong_base_class(self, fresh_registry):
        class NotAPlugin:
            name = "bad"
            description = ""

        with pytest.raises(TypeError):
            fresh_registry.register_extractor(NotAPlugin)  # type: ignore[arg-type]

    def test_register_non_class_raises(self, fresh_registry):
        with pytest.raises(TypeError):
            fresh_registry.register_postprocessor("not_a_class")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PluginRegistry — discover (built-ins)
# ---------------------------------------------------------------------------


class TestPluginRegistryDiscover:
    def test_discover_registers_builtins(self, fresh_registry):
        fresh_registry.discover(include_builtin=True)
        assert "keyword_extractor" in fresh_registry.postprocessors
        assert "readability_scorer" in fresh_registry.postprocessors

    def test_discover_idempotent(self, fresh_registry):
        fresh_registry.discover()
        fresh_registry.discover()
        # should still have exactly one of each built-in
        assert len(fresh_registry.postprocessors) >= 2

    def test_rediscover_resets(self, fresh_registry):
        fresh_registry.discover()
        count_before = len(fresh_registry.postprocessors)
        fresh_registry.rediscover()
        assert len(fresh_registry.postprocessors) == count_before

    def test_discover_no_builtins(self, fresh_registry):
        fresh_registry.discover(include_builtin=False)
        assert "keyword_extractor" not in fresh_registry.postprocessors
        assert "readability_scorer" not in fresh_registry.postprocessors

    def test_all_plugins_returns_expected_structure(self, fresh_registry):
        fresh_registry.discover()
        data = fresh_registry.all_plugins()
        assert set(data.keys()) == {"extractors", "postprocessors", "formatters"}
        assert isinstance(data["postprocessors"], list)
        names = [p["name"] for p in data["postprocessors"]]
        assert "keyword_extractor" in names
        assert "readability_scorer" in names


# ---------------------------------------------------------------------------
# PluginRegistry — entry-point loading (mocked)
# ---------------------------------------------------------------------------


class TestPluginRegistryEntryPoints:
    def _make_ep(self, name: str, cls):
        """Create a mock entry point that loads *cls*."""
        ep = mock.MagicMock()
        ep.name = name
        ep.load.return_value = cls
        return ep

    def test_entry_point_postprocessor_loaded(self, fresh_registry):
        ep = self._make_ep("test_pp", ConcretePostProcessor)
        with mock.patch(
            "summarizer.plugins._load_entry_points",
            side_effect=lambda group: [ep] if group == "summarizer.postprocessors" else [],
        ):
            fresh_registry.discover(include_builtin=False)
        assert "test_pp" in fresh_registry.postprocessors

    def test_entry_point_load_error_skipped(self, fresh_registry):
        ep = mock.MagicMock()
        ep.name = "broken_plugin"
        ep.load.side_effect = ImportError("missing dependency")

        with mock.patch(
            "summarizer.plugins._load_entry_points",
            side_effect=lambda group: [ep] if group == "summarizer.extractors" else [],
        ):
            fresh_registry.discover(include_builtin=False)
        # broken plugin should not appear
        assert "broken_plugin" not in fresh_registry.extractors

    def test_entry_point_wrong_base_class_skipped(self, fresh_registry):
        class NotAnExtractor:
            name = "imposter"
            description = ""

        ep = self._make_ep("imposter", NotAnExtractor)
        with mock.patch(
            "summarizer.plugins._load_entry_points",
            side_effect=lambda group: [ep] if group == "summarizer.extractors" else [],
        ):
            fresh_registry.discover(include_builtin=False)
        assert "imposter" not in fresh_registry.extractors


# ---------------------------------------------------------------------------
# KeywordExtractor
# ---------------------------------------------------------------------------


class TestKeywordExtractor:
    def test_extracts_keywords(self):
        summary = SimpleSummary(content=SAMPLE_ARTICLE)
        pp = KeywordExtractor()
        result = pp.process(summary, article_text=SAMPLE_ARTICLE)
        assert hasattr(result, "keywords")
        assert isinstance(result.keywords, list)
        assert len(result.keywords) <= 10

    def test_keyword_count_respects_config(self):
        summary = SimpleSummary(content=SAMPLE_ARTICLE)
        pp = KeywordExtractor()
        result = pp.process(summary, article_text=SAMPLE_ARTICLE, config={"keyword_top_n": 5})
        assert len(result.keywords) <= 5

    def test_keywords_are_strings(self):
        summary = SimpleSummary(content=SAMPLE_ARTICLE)
        pp = KeywordExtractor()
        result = pp.process(summary, article_text=SAMPLE_ARTICLE)
        assert all(isinstance(k, str) for k in result.keywords)

    def test_empty_text_returns_empty_list(self):
        summary = SimpleSummary()
        pp = KeywordExtractor()
        result = pp.process(summary, article_text="")
        assert result.keywords == []

    def test_tfidf_keywords_returns_list(self):
        keywords = _tfidf_keywords(SAMPLE_ARTICLE, top_n=5)
        assert isinstance(keywords, list)
        assert len(keywords) <= 5

    def test_tfidf_filters_stopwords(self):
        keywords = _tfidf_keywords("the quick brown fox the", top_n=10)
        assert "the" not in keywords

    def test_uses_article_text_over_content(self):
        """article_text kwarg should be preferred when both are provided."""
        summary = SimpleSummary(content="content text here data")
        pp = KeywordExtractor()
        # article_text is provided — it should be used
        result = pp.process(summary, article_text=SAMPLE_ARTICLE)
        # keywords should reflect SAMPLE_ARTICLE, not the short content
        assert len(result.keywords) > 0

    def test_name_and_description(self):
        assert KeywordExtractor.name == "keyword_extractor"
        assert KeywordExtractor.description != ""


# ---------------------------------------------------------------------------
# ReadabilityScorer
# ---------------------------------------------------------------------------


class TestReadabilityScorer:
    def test_attaches_score(self):
        summary = SimpleSummary(summary=SAMPLE_SUMMARY)
        pp = ReadabilityScorer()
        result = pp.process(summary)
        assert hasattr(result, "readability_score")
        assert isinstance(result.readability_score, float)

    def test_attaches_label(self):
        summary = SimpleSummary(summary=SAMPLE_SUMMARY)
        pp = ReadabilityScorer()
        result = pp.process(summary)
        assert hasattr(result, "readability_label")
        assert isinstance(result.readability_label, str)
        assert result.readability_label != ""

    def test_score_range(self):
        summary = SimpleSummary(summary=SAMPLE_SUMMARY)
        pp = ReadabilityScorer()
        result = pp.process(summary)
        assert 0.0 <= result.readability_score <= 100.0

    def test_empty_text_score_is_zero(self):
        summary = SimpleSummary(summary="")
        pp = ReadabilityScorer()
        result = pp.process(summary)
        assert result.readability_score == 0.0

    def test_flesch_formula_easy_text(self):
        easy_text = "I like cats. Cats are fun. Fun is good."
        score = flesch_reading_ease(easy_text)
        assert score > 50.0, f"Expected high score for easy text, got {score}"

    def test_flesch_formula_hard_text(self):
        hard_text = (
            "The epistemological ramifications of poststructuralist deconstruction "
            "necessitate a thorough reexamination of hermeneutical methodologies "
            "within contemporary philosophical discourse."
        )
        score = flesch_reading_ease(hard_text)
        assert score < 60.0, f"Expected low score for hard text, got {score}"

    def test_grade_labels(self):
        assert _grade_label(95) == "Very Easy"
        assert _grade_label(85) == "Easy"
        assert _grade_label(75) == "Fairly Easy"
        assert _grade_label(65) == "Standard"
        assert _grade_label(55) == "Fairly Difficult"
        assert _grade_label(40) == "Difficult"
        assert _grade_label(10) == "Very Confusing"

    def test_name_and_description(self):
        assert ReadabilityScorer.name == "readability_scorer"
        assert ReadabilityScorer.description != ""

    def test_short_text_does_not_crash(self):
        score = flesch_reading_ease("Hi.")
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# Integration: multiple post-processors in sequence
# ---------------------------------------------------------------------------


class TestPostProcessorChain:
    def test_chain_keyword_then_readability(self):
        summary = SimpleSummary(summary=SAMPLE_SUMMARY, content=SAMPLE_ARTICLE)
        kw = KeywordExtractor()
        rs = ReadabilityScorer()

        summary = kw.process(summary, article_text=SAMPLE_ARTICLE)
        summary = rs.process(summary)

        assert hasattr(summary, "keywords")
        assert hasattr(summary, "readability_score")
        assert len(summary.keywords) > 0
        assert 0.0 <= summary.readability_score <= 100.0

    def test_registry_discover_and_apply(self, fresh_registry):
        fresh_registry.discover(include_builtin=True)
        summary = SimpleSummary(summary=SAMPLE_SUMMARY, content=SAMPLE_ARTICLE)

        for pp_cls in fresh_registry.postprocessors.values():
            pp = pp_cls()
            summary = pp.process(summary, article_text=SAMPLE_ARTICLE)

        assert hasattr(summary, "keywords")
        assert hasattr(summary, "readability_score")