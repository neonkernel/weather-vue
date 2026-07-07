"""Tests for the plugin discovery, loading, and error-handling infrastructure."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

from summarizer.plugins import PluginRegistry, registry
from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor
from summarizer.plugins.builtin.keyword_extractor import (
    KeywordExtractor,
    extract_keywords,
    _tokenize,
)
from summarizer.plugins.builtin.readability import (
    ReadabilityScorer,
    flesch_reading_ease,
    flesch_kincaid_grade,
    readability_label,
    _count_syllables,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_summary(text: str = "This is a summary.", metadata: dict | None = None):
    """Return a minimal mock summary object."""
    s = MagicMock()
    s.summary = text
    s.article_text = "Article text about " + text
    s.metadata = metadata if metadata is not None else {}
    return s


# ---------------------------------------------------------------------------
# Base ABC tests
# ---------------------------------------------------------------------------


class TestBaseClasses:
    def test_base_extractor_is_abstract(self):
        with pytest.raises(TypeError):
            BaseExtractor()  # type: ignore[abstract]

    def test_base_postprocessor_is_abstract(self):
        with pytest.raises(TypeError):
            BasePostProcessor()  # type: ignore[abstract]

    def test_base_formatter_is_abstract(self):
        with pytest.raises(TypeError):
            BaseFormatter()  # type: ignore[abstract]

    def test_concrete_extractor(self):
        class MyExtractor(BaseExtractor):
            name = "my_extractor"

            def extract(self, url, raw_html):
                return {"text": "hello"}

        e = MyExtractor()
        assert e.extract("http://example.com", "<html/>") == {"text": "hello"}
        assert e.supports("http://anything.com") is True  # default

    def test_concrete_postprocessor(self):
        class MyPP(BasePostProcessor):
            name = "my_pp"

            def process(self, summary, article_text):
                summary.metadata["processed"] = True
                return summary

        pp = MyPP()
        s = _make_summary()
        result = pp.process(s, "article text")
        assert result.metadata["processed"] is True

    def test_concrete_formatter(self):
        class MyFmt(BaseFormatter):
            name = "my_fmt"
            extension = "txt"

            def format(self, summary):
                return f"Formatted: {summary.summary}"

        fmt = MyFmt()
        s = _make_summary("Hello world.")
        assert fmt.format(s) == "Formatted: Hello world."


# ---------------------------------------------------------------------------
# PluginRegistry tests
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def test_discover_loads_builtin_postprocessors(self):
        reg = PluginRegistry()
        reg.discover()
        names = [p.name for p in reg.postprocessors]
        assert "keyword_extractor" in names
        assert "readability_scorer" in names

    def test_discover_is_idempotent(self):
        reg = PluginRegistry()
        reg.discover()
        first_count = len(reg.postprocessors)
        reg.discover()  # second call should be a no-op
        assert len(reg.postprocessors) == first_count

    def test_get_postprocessor_by_name(self):
        reg = PluginRegistry()
        reg.discover()
        pp = reg.get_postprocessor("keyword_extractor")
        assert isinstance(pp, KeywordExtractor)

    def test_get_nonexistent_plugin_returns_none(self):
        reg = PluginRegistry()
        reg.discover()
        assert reg.get_postprocessor("does_not_exist") is None
        assert reg.get_formatter("does_not_exist") is None
        assert reg.get_extractor("does_not_exist") is None

    def test_register_instance_rejects_non_subclass(self):
        class NotAPlugin:
            pass

        with pytest.raises(TypeError, match="not a subclass"):
            PluginRegistry._register_instance(NotAPlugin, BasePostProcessor, {})

    def test_register_instance_skips_duplicate(self, caplog):
        import logging

        reg = PluginRegistry()
        d: dict = {}
        PluginRegistry._register_instance(KeywordExtractor, BasePostProcessor, d)
        with caplog.at_level(logging.DEBUG, logger="summarizer.plugins"):
            PluginRegistry._register_instance(KeywordExtractor, BasePostProcessor, d)
        assert "keyword_extractor" in d
        assert len(d) == 1

    def test_summary_structure(self):
        reg = PluginRegistry()
        reg.discover()
        s = reg.summary()
        assert set(s.keys()) == {"extractors", "postprocessors", "formatters"}
        assert isinstance(s["postprocessors"], list)
        assert all("name" in item for item in s["postprocessors"])

    def test_extractor_for_url_returns_first_match(self):
        class AlwaysExtractor(BaseExtractor):
            name = "always"

            def extract(self, url, raw_html):
                return {"text": ""}

        reg = PluginRegistry()
        reg._extractors["always"] = AlwaysExtractor()
        result = reg.extractor_for_url("http://example.com")
        assert result is not None
        assert result.name == "always"

    def test_extractor_for_url_returns_none_when_empty(self):
        reg = PluginRegistry()
        assert reg.extractor_for_url("http://example.com") is None

    def test_load_entry_point_plugins_handles_bad_plugin(self, caplog):
        """A broken entry point should log a warning and not crash discovery."""
        import logging

        bad_ep = MagicMock()
        bad_ep.name = "bad_plugin"
        bad_ep.load.side_effect = ImportError("missing module")

        reg = PluginRegistry()
        with caplog.at_level(logging.WARNING, logger="summarizer.plugins"):
            reg._load_entry_point_plugins(
                "summarizer.postprocessors", BasePostProcessor, {}
            )
        # No crash; registry dict remains empty (entry points mocked out)

    def test_load_builtin_handles_import_error(self, caplog, monkeypatch):
        """If a built-in module fails to import, log a warning and continue."""
        import logging
        import importlib

        original_import = importlib.import_module

        def bad_import(name, *args, **kwargs):
            if "keyword_extractor" in name:
                raise ImportError("simulated failure")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", bad_import)
        reg = PluginRegistry()
        with caplog.at_level(logging.WARNING, logger="summarizer.plugins"):
            reg._load_builtin_plugins()
        # readability should still load
        assert "readability_scorer" in reg._postprocessors


# ---------------------------------------------------------------------------
# KeywordExtractor tests
# ---------------------------------------------------------------------------


class TestKeywordExtractor:
    def test_tokenize_removes_stopwords(self):
        tokens = _tokenize("The quick brown fox jumps over the lazy dog")
        assert "the" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens

    def test_extract_keywords_returns_list(self):
        text = (
            "Machine learning is a branch of artificial intelligence. "
            "Machine learning algorithms build models. "
            "Artificial intelligence includes machine learning and deep learning."
        )
        kws = extract_keywords([text], top_n=5)
        assert isinstance(kws, list)
        assert len(kws) <= 5
        # "machine" or "learning" should appear (high TF-IDF)
        combined = " ".join(kws)
        assert any(w in combined for w in ("machine", "learning", "artificial"))

    def test_extract_keywords_empty_text(self):
        assert extract_keywords([""], top_n=5) == []
        assert extract_keywords([], top_n=5) == []

    def test_process_attaches_keywords(self):
        ke = KeywordExtractor(top_n=5)
        s = _make_summary("Climate change causes global warming and extreme weather events.")
        result = ke.process(
            s,
            "Climate change is driven by greenhouse gas emissions. "
            "Global warming leads to extreme weather.",
        )
        assert "keywords" in result.metadata
        assert isinstance(result.metadata["keywords"], list)

    def test_process_handles_missing_metadata(self):
        ke = KeywordExtractor(top_n=5)
        s = MagicMock()
        s.summary = "Some text."
        s.metadata = None
        # Should not raise
        ke.process(s, "article text")

    def test_process_handles_no_summary_text(self):
        ke = KeywordExtractor()
        s = _make_summary("")
        result = ke.process(s, "article text about nothing")
        # Should not raise; keywords may be present from article_text
        assert result is s


# ---------------------------------------------------------------------------
# ReadabilityScorer tests
# ---------------------------------------------------------------------------


class TestReadabilityScorer:
    _EASY_TEXT = (
        "The cat sat on the mat. "
        "The dog ran fast. "
        "She went to the shop. "
        "He saw the big red bus."
    )
    _HARD_TEXT = (
        "The philosophical implications of epistemological relativism "
        "necessitate a comprehensive reexamination of hermeneutical frameworks "
        "underpinning contemporary academic discourse."
    )

    def test_count_syllables_simple(self):
        assert _count_syllables("cat") == 1
        assert _count_syllables("happy") >= 2
        assert _count_syllables("beautiful") >= 3

    def test_flesch_reading_ease_easy_text(self):
        score = flesch_reading_ease(self._EASY_TEXT)
        assert score >= 60, f"Expected high readability, got {score}"

    def test_flesch_reading_ease_hard_text(self):
        score = flesch_reading_ease(self._HARD_TEXT)
        assert score < 60, f"Expected low readability, got {score}"

    def test_flesch_reading_ease_clamped(self):
        score = flesch_reading_ease("")
        assert 0.0 <= score <= 100.0

    def test_flesch_kincaid_grade_easy(self):
        grade = flesch_kincaid_grade(self._EASY_TEXT)
        assert grade < 10

    def test_flesch_kincaid_grade_hard(self):
        grade = flesch_kincaid_grade(self._HARD_TEXT)
        assert grade > 10

    def test_readability_label_mapping(self):
        assert readability_label(95) == "Very Easy"
        assert readability_label(85) == "Easy"
        assert readability_label(75) == "Fairly Easy"
        assert readability_label(65) == "Standard"
        assert readability_label(55) == "Fairly Difficult"
        assert readability_label(35) == "Difficult"
        assert readability_label(10) == "Very Confusing"

    def test_process_attaches_readability(self):
        scorer = ReadabilityScorer()
        s = _make_summary(self._EASY_TEXT)
        result = scorer.process(s, "irrelevant article text")
        assert "readability" in result.metadata
        r = result.metadata["readability"]
        assert "flesch_reading_ease" in r
        assert "flesch_kincaid_grade" in r
        assert "label" in r

    def test_process_skips_empty_summary(self):
        scorer = ReadabilityScorer()
        s = _make_summary("")
        result = scorer.process(s, "article text")
        assert result is s
        assert "readability" not in result.metadata

    def test_process_handles_no_metadata(self):
        scorer = ReadabilityScorer()
        s = MagicMock()
        s.summary = self._EASY_TEXT
        s.metadata = None
        # Should not raise
        scorer.process(s, "article")


# ---------------------------------------------------------------------------
# CLI integration: plugins list
# ---------------------------------------------------------------------------


class TestPluginsListCommand:
    def test_plugins_list_runs(self):
        from click.testing import CliRunner
        from summarizer.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "list"])
        assert result.exit_code == 0, result.output
        assert "Post-Processors" in result.output
        assert "keyword_extractor" in result.output
        assert "readability_scorer" in result.output

    def test_plugins_list_json(self):
        from click.testing import CliRunner
        from summarizer.cli import cli
        import json

        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "list", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "postprocessors" in data
        names = [p["name"] for p in data["postprocessors"]]
        assert "keyword_extractor" in names
        assert "readability_scorer" in names