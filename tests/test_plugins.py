"""
Tests for the plugin system: discovery, loading, validation, and error handling.

These tests use only the programmatic registration API (no entry points) so they
work without any package installation.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from summarizer.plugins import PluginLoadError, PluginRegistry
from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor
from summarizer.plugins.builtin.keyword_extractor import (
    KeywordExtractor,
    _compute_tfidf,
    _tokenize,
)
from summarizer.plugins.builtin.readability import (
    ReadabilityScorer,
    _compute_flesch,
    _count_sentences,
    _count_syllables,
    _count_words,
    _grade_label,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_summary(text: str = "This is a test summary.", title: str = "Test"):
    """Create a minimal mock Summary-like object."""
    summary = MagicMock()
    summary.summary = text
    summary.title = title
    summary.metadata = {}
    return summary


# ---------------------------------------------------------------------------
# Concrete implementations used in tests
# ---------------------------------------------------------------------------


class GoodExtractor(BaseExtractor):
    name = "good_extractor"
    description = "A working extractor."

    def can_handle(self, source: str) -> bool:
        return source.startswith("http://")

    def extract(self, source: str) -> dict:
        return {"text": "article content", "title": "Title", "url": source}


class GoodPostProcessor(BasePostProcessor):
    name = "good_postprocessor"
    description = "Appends a marker to summary."

    def process(self, summary, article_text: str = ""):
        summary.metadata["processed"] = True
        return summary


class GoodFormatter(BaseFormatter):
    name = "good_formatter"
    description = "Returns a simple string."
    extension = ".txt"

    def format(self, summary, **kwargs) -> str:
        return f"FORMATTED: {getattr(summary, 'summary', '')}"


# Bad plugins that don't inherit from the correct base
class NotAPlugin:
    pass


class NotAnExtractor(BasePostProcessor):
    name = "not_an_extractor"

    def process(self, summary, article_text: str = ""):
        return summary


# ---------------------------------------------------------------------------
# PluginRegistry – basic registration
# ---------------------------------------------------------------------------


class TestPluginRegistryRegistration:
    def setup_method(self):
        # Fresh registry with no auto-discovery to keep tests isolated
        self.reg = PluginRegistry(autoload=False)

    def test_register_extractor(self):
        self.reg.register_extractor(GoodExtractor)
        extractors = self.reg.get_extractors()
        assert len(extractors) == 1
        assert extractors[0].name == "good_extractor"

    def test_register_postprocessor(self):
        self.reg.register_postprocessor(GoodPostProcessor)
        pps = self.reg.get_postprocessors()
        assert len(pps) == 1
        assert pps[0].name == "good_postprocessor"

    def test_register_formatter(self):
        self.reg.register_formatter(GoodFormatter)
        fmts = self.reg.get_formatters()
        assert len(fmts) == 1
        assert fmts[0].name == "good_formatter"

    def test_get_extractor_by_name(self):
        self.reg.register_extractor(GoodExtractor)
        ext = self.reg.get_extractor("good_extractor")
        assert ext is not None
        assert ext.name == "good_extractor"

    def test_get_nonexistent_extractor_returns_none(self):
        assert self.reg.get_extractor("does_not_exist") is None

    def test_get_postprocessor_by_name(self):
        self.reg.register_postprocessor(GoodPostProcessor)
        pp = self.reg.get_postprocessor("good_postprocessor")
        assert pp is not None

    def test_get_formatter_by_name(self):
        self.reg.register_formatter(GoodFormatter)
        fmt = self.reg.get_formatter("good_formatter")
        assert fmt is not None
        assert fmt.name == "good_formatter"

    def test_repr(self):
        self.reg.register_extractor(GoodExtractor)
        r = repr(self.reg)
        assert "extractors=1" in r
        assert "postprocessors=0" in r


# ---------------------------------------------------------------------------
# PluginRegistry – error handling / validation
# ---------------------------------------------------------------------------


class TestPluginRegistryValidation:
    def setup_method(self):
        self.reg = PluginRegistry(autoload=False)

    def test_register_non_extractor_raises(self):
        with pytest.raises(PluginLoadError, match="BaseExtractor"):
            self.reg.register_extractor(NotAPlugin)

    def test_register_non_postprocessor_raises(self):
        with pytest.raises(PluginLoadError, match="BasePostProcessor"):
            self.reg.register_postprocessor(NotAPlugin)

    def test_register_non_formatter_raises(self):
        with pytest.raises(PluginLoadError, match="BaseFormatter"):
            self.reg.register_formatter(NotAPlugin)

    def test_register_wrong_base_type_for_extractor(self):
        # NotAnExtractor inherits from BasePostProcessor, not BaseExtractor
        with pytest.raises(PluginLoadError, match="BaseExtractor"):
            self.reg.register_extractor(NotAnExtractor)

    def test_register_instance_instead_of_class_raises(self):
        instance = GoodExtractor()
        with pytest.raises(PluginLoadError):
            self.reg.register_extractor(instance)  # type: ignore[arg-type]

    def test_overwrite_logs_warning(self, caplog):
        import logging
        self.reg.register_extractor(GoodExtractor)
        with caplog.at_level(logging.WARNING):
            self.reg.register_extractor(GoodExtractor)
        assert any("Overwriting" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# PluginRegistry – list_all
# ---------------------------------------------------------------------------


class TestPluginRegistryListAll:
    def setup_method(self):
        self.reg = PluginRegistry(autoload=False)

    def test_list_all_empty(self):
        result = self.reg.list_all()
        assert result["extractors"] == []
        assert result["postprocessors"] == []
        assert result["formatters"] == []

    def test_list_all_populated(self):
        self.reg.register_extractor(GoodExtractor)
        self.reg.register_postprocessor(GoodPostProcessor)
        self.reg.register_formatter(GoodFormatter)

        result = self.reg.list_all()
        assert len(result["extractors"]) == 1
        assert result["extractors"][0]["name"] == "good_extractor"
        assert len(result["postprocessors"]) == 1
        assert len(result["formatters"]) == 1

    def test_list_all_has_class_field(self):
        self.reg.register_extractor(GoodExtractor)
        result = self.reg.list_all()
        assert "class" in result["extractors"][0]
        assert "GoodExtractor" in result["extractors"][0]["class"]


# ---------------------------------------------------------------------------
# PluginRegistry – entry point discovery (mocked)
# ---------------------------------------------------------------------------


class TestPluginRegistryDiscovery:
    def _make_mock_ep(self, name: str, cls):
        ep = MagicMock()
        ep.name = name
        ep.value = f"test.module:{cls.__name__}"
        ep.load.return_value = cls
        return ep

    def test_discovers_postprocessor_via_entry_points(self):
        ep = self._make_mock_ep("good_pp", GoodPostProcessor)

        with patch(
            "summarizer.plugins._load_entry_points",
            side_effect=lambda group: (
                [ep] if group == "summarizer.postprocessors" else []
            ),
        ):
            reg = PluginRegistry(autoload=True)

        pps = reg.get_postprocessors()
        assert any(p.name == "good_postprocessor" for p in pps)

    def test_bad_entry_point_load_logs_error(self, caplog):
        import logging

        bad_ep = MagicMock()
        bad_ep.name = "bad_plugin"
        bad_ep.value = "nonexistent.module:NonExistentClass"
        bad_ep.load.side_effect = ImportError("module not found")

        with caplog.at_level(logging.ERROR):
            with patch(
                "summarizer.plugins._load_entry_points",
                side_effect=lambda group: (
                    [bad_ep] if group == "summarizer.extractors" else []
                ),
            ):
                reg = PluginRegistry(autoload=True)

        assert any("load error" in r.message.lower() for r in caplog.records)
        # Registry should still be usable
        assert reg.get_extractors() == []

    def test_malformed_plugin_class_logs_error(self, caplog):
        """An entry point that returns a non-subclass should be rejected."""
        import logging

        ep = self._make_mock_ep("bad_class", NotAPlugin)

        with caplog.at_level(logging.ERROR):
            with patch(
                "summarizer.plugins._load_entry_points",
                side_effect=lambda group: (
                    [ep] if group == "summarizer.extractors" else []
                ),
            ):
                reg = PluginRegistry(autoload=True)

        assert reg.get_extractors() == []


# ---------------------------------------------------------------------------
# BaseExtractor ABC contract
# ---------------------------------------------------------------------------


class TestBaseExtractor:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BaseExtractor()  # type: ignore[abstract]

    def test_concrete_implementation_works(self):
        ext = GoodExtractor()
        assert ext.can_handle("http://example.com") is True
        assert ext.can_handle("ftp://nope.com") is False
        result = ext.extract("http://example.com")
        assert "text" in result

    def test_name_and_description_attributes(self):
        ext = GoodExtractor()
        assert ext.name == "good_extractor"
        assert "working" in ext.description


# ---------------------------------------------------------------------------
# BasePostProcessor ABC contract
# ---------------------------------------------------------------------------


class TestBasePostProcessor:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BasePostProcessor()  # type: ignore[abstract]

    def test_concrete_process_called(self):
        pp = GoodPostProcessor()
        summary = _make_summary()
        result = pp.process(summary)
        assert result.metadata["processed"] is True


# ---------------------------------------------------------------------------
# BaseFormatter ABC contract
# ---------------------------------------------------------------------------


class TestBaseFormatter:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BaseFormatter()  # type: ignore[abstract]

    def test_format_called(self):
        fmt = GoodFormatter()
        summary = _make_summary("Hello world")
        result = fmt.format(summary)
        assert "FORMATTED:" in result
        assert "Hello world" in result

    def test_format_many_default_implementation(self):
        fmt = GoodFormatter()
        summaries = [_make_summary("First"), _make_summary("Second")]
        result = fmt.format_many(summaries)
        assert "First" in result
        assert "Second" in result
        assert "\n\n" in result


# ---------------------------------------------------------------------------
# KeywordExtractor
# ---------------------------------------------------------------------------


class TestKeywordExtractor:
    def test_tokenize_basic(self):
        tokens = _tokenize("Hello, World! This is a test.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "this" in tokens

    def test_tokenize_removes_punctuation(self):
        tokens = _tokenize("Hello, World!")
        assert "," not in tokens
        assert "!" not in tokens

    def test_tokenize_handles_hyphens(self):
        tokens = _tokenize("state-of-the-art technology")
        assert "state" in tokens
        assert "art" in tokens
        assert "technology" in tokens

    def test_compute_tfidf_returns_sorted_by_score(self):
        tokens = ["python", "python", "python", "code", "code", "language"]
        stopwords = frozenset()
        result = _compute_tfidf(tokens, stopwords, top_n=3)
        assert len(result) <= 3
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_compute_tfidf_filters_stopwords(self):
        tokens = ["the", "a", "python", "is", "great"]
        stopwords = frozenset({"the", "a", "is"})
        result = _compute_tfidf(tokens, stopwords, top_n=10)
        terms = [r["term"] for r in result]
        assert "the" not in terms
        assert "a" not in terms
        assert "python" in terms

    def test_compute_tfidf_empty_input(self):
        result = _compute_tfidf([], frozenset(), top_n=10)
        assert result == []

    def test_process_attaches_keywords(self):
        extractor = KeywordExtractor(top_n=5)
        article = (
            "Python is a powerful programming language. "
            "Python is used for data science and machine learning. "
            "Many developers love Python for its simplicity."
        )
        summary = _make_summary()
        result = extractor.process(summary, article_text=article)
        assert "keywords" in result.metadata
        assert isinstance(result.metadata["keywords"], list)
        assert len(result.metadata["keywords"]) <= 5

    def test_process_returns_summary_unchanged_if_no_text(self):
        extractor = KeywordExtractor()
        summary = _make_summary(text="")
        summary.summary = ""
        result = extractor.process(summary, article_text="")
        # metadata may or may not have keywords key; no crash
        assert result is summary

    def test_process_falls_back_to_summary_text(self):
        extractor = KeywordExtractor(top_n=3)
        summary = _make_summary("Machine learning models require large datasets.")
        result = extractor.process(summary, article_text="")
        assert "keywords" in result.metadata

    def test_keyword_results_have_term_and_score_fields(self):
        extractor = KeywordExtractor(top_n=5)
        article = "Deep learning neural networks are trained on large datasets."
        summary = _make_summary()
        result = extractor.process(summary, article_text=article)
        for kw in result.metadata.get("keywords", []):
            assert "term" in kw
            assert "score" in kw
            assert isinstance(kw["score"], float)

    def test_name_and_description(self):
        extractor = KeywordExtractor()
        assert extractor.name == "keyword_extractor"
        assert extractor.description != ""

    def test_is_subclass_of_base_post_processor(self):
        assert issubclass(KeywordExtractor, BasePostProcessor)


# ---------------------------------------------------------------------------
# ReadabilityScorer
# ---------------------------------------------------------------------------


class TestReadabilityScorer:
    def test_count_words_basic(self):
        assert _count_words("Hello world") == 2

    def test_count_words_empty(self):
        assert _count_words("") == 1  # min 1

    def test_count_sentences_basic(self):
        assert _count_sentences("Hello. World. Foo.") == 3

    def test_count_sentences_exclamation(self):
        count = _count_sentences("Hello! How are you? I am fine.")
        assert count == 3

    def test_count_sentences_empty(self):
        assert _count_sentences("") == 1  # min 1

    def test_count_syllables_simple(self):
        # "hello" has 2 syllables (hel-lo)
        count = _count_syllables("hello")
        assert count >= 1

    def test_count_syllables_single_vowel_word(self):
        # "cat" has 1 syllable
        count = _count_syllables("cat")
        assert count == 1

    def test_compute_flesch_returns_tuple(self):
        text = "The cat sat on the mat. It was a fat cat."
        ease, grade = _compute_flesch(text)
        assert isinstance(ease, float)
        assert isinstance(grade, float)

    def test_compute_flesch_ease_in_valid_range(self):
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "Pack my box with five dozen liquor jugs."
        )
        ease, _ = _compute_flesch(text)
        assert 0.0 <= ease <= 100.0

    def test_grade_label_very_easy(self):
        assert _grade_label(95.0) == "Very Easy"

    def test_grade_label_easy(self):
        assert _grade_label(85.0) == "Easy"

    def test_grade_label_standard(self):
        assert _grade_label(65.0) == "Standard"

    def test_grade_label_difficult(self):
        assert _grade_label(40.0) == "Difficult"

    def test_grade_label_very_confusing(self):
        assert _grade_label(10.0) == "Very Confusing"

    def test_process_attaches_readability_metadata(self):
        scorer = ReadabilityScorer()
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "Machine learning is a subset of artificial intelligence."
        )
        summary = _make_summary(text)
        result = scorer.process(summary, article_text="ignored")
        assert "readability" in result.metadata
        r = result.metadata["readability"]
        assert "flesch_ease" in r
        assert "flesch_kincaid_grade" in r
        assert "label" in r
        assert "word_count" in r
        assert "sentence_count" in r
        assert "syllable_count" in r

    def test_process_skips_empty_summary(self):
        scorer = ReadabilityScorer()
        summary = _make_summary("")
        summary.summary = ""
        result = scorer.process(summary)
        assert "readability" not in result.metadata

    def test_readability_ease_is_float(self):
        scorer = ReadabilityScorer()
        summary = _make_summary("Simple short sentence.")
        result = scorer.process(summary)
        assert isinstance(result.metadata["readability"]["flesch_ease"], float)

    def test_name_and_description(self):
        scorer = ReadabilityScorer()
        assert scorer.name == "readability_scorer"
        assert "Flesch" in scorer.description

    def test_is_subclass_of_base_post_processor(self):
        assert issubclass(ReadabilityScorer, BasePostProcessor)


# ---------------------------------------------------------------------------
# Integration: registry with builtin plugins
# ---------------------------------------------------------------------------


class TestBuiltinPluginIntegration:
    def setup_method(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        self.reg = PluginRegistry(autoload=False)
        self.reg.register_postprocessor(KeywordExtractor)
        self.reg.register_postprocessor(ReadabilityScorer)

    def test_both_postprocessors_registered(self):
        pps = self.reg.get_postprocessors()
        names = [p.name for p in pps]
        assert "keyword_extractor" in names
        assert "readability_scorer" in names

    def test_pipeline_applies_both(self):
        article = (
            "Artificial intelligence is transforming the technology industry. "
            "Companies are investing billions of dollars into machine learning research. "
            "Developers must understand algorithms and data structures."
        )
        summary_text = (
            "AI is transforming tech. Companies invest in ML. "
            "Developers need algorithm knowledge."
        )
        summary = _make_summary(summary_text)

        pps = self.reg.get_postprocessors()
        for pp in pps:
            summary = pp.process(summary, article_text=article)

        assert "keywords" in summary.metadata
        assert "readability" in summary.metadata

    def test_list_all_shows_both(self):
        result = self.reg.list_all()
        pp_names = [p["name"] for p in result["postprocessors"]]
        assert "keyword_extractor" in pp_names
        assert "readability_scorer" in pp_names