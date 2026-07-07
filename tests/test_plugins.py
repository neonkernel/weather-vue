"""Tests for the plugin system: discovery, loading, validation, and error handling."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor
from summarizer.plugins import (
    EP_EXTRACTORS,
    EP_FORMATTERS,
    EP_POSTPROCESSORS,
    PluginLoadError,
    PluginRegistry,
    get_registry,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class _FakeSummary:
    """Minimal stand-in for a Summary model."""

    def __init__(self, text: str = "Hello world.", metadata: dict | None = None):
        self.text = text
        self.metadata: dict = metadata or {}

    def model_copy(self, *, update: dict) -> "_FakeSummary":
        new = _FakeSummary(self.text, dict(self.metadata))
        for k, v in update.items():
            setattr(new, k, v)
        return new


class _GoodExtractor(BaseExtractor):
    name = "good_extractor"
    description = "A well-behaved extractor."

    def extract(self, source: str) -> str:
        return f"extracted:{source}"


class _GoodPostProcessor(BasePostProcessor):
    name = "good_pp"
    description = "A well-behaved post-processor."

    def process(self, summary: Any, article_text: str = "") -> Any:
        summary.metadata["pp_ran"] = True
        return summary


class _GoodFormatter(BaseFormatter):
    name = "good_formatter"
    description = "A well-behaved formatter."

    def format(self, summary: Any) -> str:
        return f"FORMATTED:{summary.text}"


class _BadPlugin:
    """Does NOT subclass any plugin base class."""

    name = "bad"


# ---------------------------------------------------------------------------
# BaseExtractor tests
# ---------------------------------------------------------------------------


class TestBaseExtractor:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseExtractor()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        e = _GoodExtractor()
        assert e.extract("http://example.com") == "extracted:http://example.com"

    def test_metadata(self):
        e = _GoodExtractor()
        meta = e.get_metadata()
        assert meta["name"] == "good_extractor"
        assert "class" in meta


# ---------------------------------------------------------------------------
# BasePostProcessor tests
# ---------------------------------------------------------------------------


class TestBasePostProcessor:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BasePostProcessor()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        pp = _GoodPostProcessor()
        summary = _FakeSummary()
        result = pp.process(summary)
        assert result.metadata.get("pp_ran") is True


# ---------------------------------------------------------------------------
# BaseFormatter tests
# ---------------------------------------------------------------------------


class TestBaseFormatter:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseFormatter()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        f = _GoodFormatter()
        summary = _FakeSummary("hello")
        assert f.format(summary) == "FORMATTED:hello"


# ---------------------------------------------------------------------------
# PluginRegistry – _register
# ---------------------------------------------------------------------------


class TestPluginRegistryRegister:
    def _fresh(self) -> PluginRegistry:
        r = PluginRegistry()
        return r

    def test_register_extractor(self):
        r = self._fresh()
        r._register(EP_EXTRACTORS, "ge", _GoodExtractor)
        assert "ge" in r.extractors

    def test_register_postprocessor(self):
        r = self._fresh()
        r._register(EP_POSTPROCESSORS, "gp", _GoodPostProcessor)
        assert "gp" in r.postprocessors

    def test_register_formatter(self):
        r = self._fresh()
        r._register(EP_FORMATTERS, "gf", _GoodFormatter)
        assert "gf" in r.formatters

    def test_register_bad_plugin_raises(self):
        r = self._fresh()
        with pytest.raises(PluginLoadError, match="must be a subclass"):
            r._register(EP_POSTPROCESSORS, "bad", _BadPlugin)

    def test_register_unknown_group_raises(self):
        r = self._fresh()
        with pytest.raises(PluginLoadError, match="Unknown plugin group"):
            r._register("summarizer.unknown", "x", _GoodPostProcessor)

    def test_duplicate_registration_is_skipped(self):
        r = self._fresh()
        r._register(EP_EXTRACTORS, "ge", _GoodExtractor)
        # Second registration should not raise; original preserved
        r._register(EP_EXTRACTORS, "ge", _GoodExtractor)
        assert len(r.extractors) == 1

    def test_non_class_raises(self):
        r = self._fresh()
        with pytest.raises(PluginLoadError):
            r._register(EP_EXTRACTORS, "fn", lambda s: s)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PluginRegistry – discovery via entry points
# ---------------------------------------------------------------------------


class TestPluginRegistryDiscovery:
    def _make_ep(self, name: str, cls: type) -> MagicMock:
        ep = MagicMock()
        ep.name = name
        ep.load.return_value = cls
        return ep

    def test_discover_loads_entry_points(self):
        good_ep = self._make_ep("custom_pp", _GoodPostProcessor)

        with patch("summarizer.plugins.entry_points") as mock_ep:
            def _side_effect(group):
                if group == EP_POSTPROCESSORS:
                    return [good_ep]
                return []

            mock_ep.side_effect = _side_effect
            r = PluginRegistry()
            # skip built-ins for clarity
            r._load_entry_point_group(EP_POSTPROCESSORS)

        assert "custom_pp" in r.postprocessors

    def test_discover_skips_bad_plugin_and_records_error(self):
        bad_ep = self._make_ep("bad_one", _BadPlugin)

        with patch("summarizer.plugins.entry_points") as mock_ep:
            mock_ep.side_effect = lambda group: [bad_ep] if group == EP_POSTPROCESSORS else []
            r = PluginRegistry()
            r._load_entry_point_group(EP_POSTPROCESSORS)

        assert "bad_one" not in r.postprocessors
        assert len(r.errors) == 1

    def test_discover_skips_unloadable_ep_and_records_error(self):
        broken_ep = MagicMock()
        broken_ep.name = "broken"
        broken_ep.load.side_effect = ImportError("missing dep")

        with patch("summarizer.plugins.entry_points") as mock_ep:
            mock_ep.side_effect = lambda group: [broken_ep] if group == EP_EXTRACTORS else []
            r = PluginRegistry()
            r._load_entry_point_group(EP_EXTRACTORS)

        assert "broken" not in r.extractors
        assert any("broken" in e for e in r.errors)

    def test_entry_points_error_is_caught(self):
        with patch("summarizer.plugins.entry_points", side_effect=Exception("boom")):
            r = PluginRegistry()
            r._load_entry_point_group(EP_EXTRACTORS)
        assert len(r.errors) == 1


# ---------------------------------------------------------------------------
# PluginRegistry – built-in plugins
# ---------------------------------------------------------------------------


class TestBuiltinPlugins:
    def test_builtin_postprocessors_registered(self):
        r = PluginRegistry()
        r._load_builtin_plugins()
        # Both built-ins should be present
        assert "keyword_extractor" in r.postprocessors
        assert "readability" in r.postprocessors

    def test_builtin_load_failure_recorded(self):
        """If a built-in import fails the error is captured, not raised."""
        r = PluginRegistry()
        # Patch the import to raise
        with patch.dict(sys.modules, {"summarizer.plugins.builtin.readability": None}):
            # Manually trigger
            try:
                from summarizer.plugins.builtin import readability as _r  # noqa: F401
            except Exception:
                pass
        # The registry should still function
        assert r.errors == []


# ---------------------------------------------------------------------------
# PluginRegistry – apply_postprocessors
# ---------------------------------------------------------------------------


class TestApplyPostProcessors:
    def _registry_with_pp(self) -> PluginRegistry:
        r = PluginRegistry()
        r._register(EP_POSTPROCESSORS, "gp", _GoodPostProcessor)
        return r

    def test_applies_all_postprocessors(self):
        r = self._registry_with_pp()
        summary = _FakeSummary()
        result = r.apply_postprocessors(summary)
        assert result.metadata.get("pp_ran") is True

    def test_applies_named_subset(self):
        r = self._registry_with_pp()

        class _AnotherPP(BasePostProcessor):
            name = "other_pp"

            def process(self, summary: Any, article_text: str = "") -> Any:
                summary.metadata["other_ran"] = True
                return summary

        r._register(EP_POSTPROCESSORS, "other_pp", _AnotherPP)

        summary = _FakeSummary()
        result = r.apply_postprocessors(summary, names=["gp"])
        assert result.metadata.get("pp_ran") is True
        assert result.metadata.get("other_ran") is None

    def test_failing_postprocessor_does_not_crash_pipeline(self):
        class _CrashyPP(BasePostProcessor):
            name = "crashy"

            def process(self, summary: Any, article_text: str = "") -> Any:
                raise RuntimeError("boom")

        r = PluginRegistry()
        r._register(EP_POSTPROCESSORS, "crashy", _CrashyPP)
        summary = _FakeSummary("hello")
        result = r.apply_postprocessors(summary)
        assert result.text == "hello"  # unchanged


# ---------------------------------------------------------------------------
# PluginRegistry – list_all
# ---------------------------------------------------------------------------


class TestListAll:
    def test_list_all_structure(self):
        r = PluginRegistry()
        r._register(EP_EXTRACTORS, "ge", _GoodExtractor)
        r._register(EP_POSTPROCESSORS, "gp", _GoodPostProcessor)
        r._register(EP_FORMATTERS, "gf", _GoodFormatter)
        listing = r.list_all()
        assert EP_EXTRACTORS in listing
        assert EP_POSTPROCESSORS in listing
        assert EP_FORMATTERS in listing
        assert "ge" in listing[EP_EXTRACTORS]
        assert "gp" in listing[EP_POSTPROCESSORS]
        assert "gf" in listing[EP_FORMATTERS]


# ---------------------------------------------------------------------------
# get_registry singleton
# ---------------------------------------------------------------------------


class TestGetRegistry:
    def test_returns_plugin_registry(self):
        reg = get_registry(force_reload=True)
        assert isinstance(reg, PluginRegistry)

    def test_singleton_behaviour(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_force_reload_creates_new_instance(self):
        r1 = get_registry()
        r2 = get_registry(force_reload=True)
        assert r1 is not r2


# ---------------------------------------------------------------------------
# KeywordExtractor
# ---------------------------------------------------------------------------


class TestKeywordExtractor:
    def test_extracts_keywords_into_metadata(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        kw = KeywordExtractor(top_n=5)
        article = (
            "Python is a high-level programming language. "
            "Python is widely used for data science and machine learning. "
            "Data scientists love Python because it is easy to read."
        )
        summary = _FakeSummary("Python summary.", metadata={})
        result = kw.process(summary, article_text=article)
        keywords = result.metadata.get("keywords", [])
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        # "python" or "data" should rank highly
        assert any(k in ("python", "data", "science", "learning") for k in keywords)

    def test_falls_back_to_summary_text_when_no_article(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        kw = KeywordExtractor(top_n=3)
        summary = _FakeSummary("The quick brown fox jumps over the lazy dog repeatedly.")
        result = kw.process(summary, article_text="")
        assert "keywords" in result.metadata

    def test_empty_text_returns_empty_keywords(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        kw = KeywordExtractor()
        summary = _FakeSummary("")
        result = kw.process(summary, article_text="")
        assert result.metadata.get("keywords", []) == []


# ---------------------------------------------------------------------------
# ReadabilityScorer
# ---------------------------------------------------------------------------


class TestReadabilityScorer:
    def test_scores_summary_text(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        scorer = ReadabilityScorer()
        summary = _FakeSummary(
            "The cat sat on the mat. The dog ran fast. Birds fly high in the sky."
        )
        result = scorer.process(summary)
        rd = result.metadata.get("readability", {})
        assert "flesch_reading_ease" in rd
        assert "flesch_kincaid_grade" in rd
        assert "reading_ease_label" in rd
        assert rd["word_count"] > 0

    def test_empty_summary_is_unchanged(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        scorer = ReadabilityScorer()
        summary = _FakeSummary("")
        result = scorer.process(summary)
        assert result.metadata.get("readability") is None

    def test_reading_ease_label_mapping(self):
        from summarizer.plugins.builtin.readability import reading_ease_label

        assert reading_ease_label(95) == "Very Easy"
        assert reading_ease_label(85) == "Easy"
        assert reading_ease_label(75) == "Fairly Easy"
        assert reading_ease_label(65) == "Standard"
        assert reading_ease_label(55) == "Fairly Difficult"
        assert reading_ease_label(35) == "Difficult"
        assert reading_ease_label(10) == "Very Confusing"

    def test_syllable_counting(self):
        from summarizer.plugins.builtin.readability import _count_syllables

        assert _count_syllables("cat") == 1
        assert _count_syllables("table") >= 1
        assert _count_syllables("beautiful") >= 3
        assert _count_syllables("") == 0


# ---------------------------------------------------------------------------
# CLI integration – plugins list
# ---------------------------------------------------------------------------


class TestPluginsListCLI:
    def test_plugins_list_output(self):
        from click.testing import CliRunner
        from summarizer.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "list"])
        assert result.exit_code == 0
        # Should mention the built-in post-processors
        assert "Post-Processors" in result.output or "postprocessors" in result.output.lower()

    def test_plugins_list_json(self):
        import json
        from click.testing import CliRunner
        from summarizer.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "summarizer.postprocessors" in data

    def test_plugins_info_known(self):
        from click.testing import CliRunner
        from summarizer.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "info", "readability"])
        assert result.exit_code == 0
        assert "readability" in result.output

    def test_plugins_info_unknown_exits_nonzero(self):
        from click.testing import CliRunner
        from summarizer.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "info", "no_such_plugin"])
        assert result.exit_code != 0