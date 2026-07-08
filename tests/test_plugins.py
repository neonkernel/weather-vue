"""
Tests for the plugin discovery, loading, and validation subsystem.

These tests cover:

* PluginRegistry – discovery, lazy loading, programmatic registration
* BaseExtractor / BasePostProcessor / BaseFormatter – ABC enforcement
* Built-in post-processors – KeywordExtractor and ReadabilityScorer
* Error handling – malformed plugins, bad entry points
* CLI ``plugins list`` command
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from summarizer.models import Summary
from summarizer.plugins import PluginLoadError, PluginRegistry, _instantiate_and_validate
from summarizer.plugins.base import BaseExtractor, BaseFormatter, BasePostProcessor
from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor
from summarizer.plugins.builtin.readability import (
    ReadabilityScorer,
    _count_sentences,
    _count_syllables_in_word,
    _count_words,
    _ease_label,
    _flesch_kincaid,
)


# ===========================================================================
# Fixtures / helpers
# ===========================================================================


def _make_summary(text: str = "This is a test summary.", metadata: dict | None = None) -> Summary:
    return Summary(text=text, source="http://example.com", metadata=metadata or {})


class _GoodExtractor(BaseExtractor):
    name = "good_extractor"
    description = "A well-behaved extractor"
    version = "1.0.0"

    def can_handle(self, source: str) -> bool:
        return source.startswith("http://")

    def extract(self, source: str, **kwargs: Any) -> str:
        return f"Content from {source}"


class _GoodPostProcessor(BasePostProcessor):
    name = "good_postprocessor"
    description = "A well-behaved post-processor"
    version = "1.0.0"

    def process(self, summary: Summary, original_text: str, **kwargs: Any) -> Summary:
        summary.metadata["processed"] = True
        return summary


class _GoodFormatter(BaseFormatter):
    name = "good_formatter"
    description = "A well-behaved formatter"
    version = "1.0.0"
    extension = ".txt"

    def format(self, summary: Summary, **kwargs: Any) -> str:
        return f"FORMATTED: {summary.text}"


# ===========================================================================
# ABC enforcement
# ===========================================================================


class TestBaseABCs:
    def test_extractor_cannot_be_instantiated_without_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseExtractor()  # type: ignore[abstract]

    def test_postprocessor_cannot_be_instantiated_without_abstract_methods(self):
        with pytest.raises(TypeError):
            BasePostProcessor()  # type: ignore[abstract]

    def test_formatter_cannot_be_instantiated_without_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseFormatter()  # type: ignore[abstract]

    def test_concrete_extractor_repr(self):
        ext = _GoodExtractor()
        assert "good_extractor" in repr(ext)
        assert "1.0.0" in repr(ext)

    def test_concrete_postprocessor_repr(self):
        pp = _GoodPostProcessor()
        assert "good_postprocessor" in repr(pp)

    def test_concrete_formatter_repr(self):
        fmt = _GoodFormatter()
        assert "good_formatter" in repr(fmt)


# ===========================================================================
# PluginRegistry – programmatic registration
# ===========================================================================


class TestPluginRegistry:
    def _fresh_registry(self) -> PluginRegistry:
        """Return a registry with an empty discovery (no real entry points)."""
        reg = PluginRegistry()
        with patch("summarizer.plugins._get_entry_points", return_value=[]):
            reg.discover()
        return reg

    def test_discover_sets_discovered_flag(self):
        reg = self._fresh_registry()
        assert reg._discovered is True

    def test_empty_registry_returns_empty_lists(self):
        reg = self._fresh_registry()
        assert reg.extractors == []
        assert reg.postprocessors == []
        assert reg.formatters == []

    def test_register_extractor(self):
        reg = self._fresh_registry()
        ext = _GoodExtractor()
        reg.register_extractor(ext)
        assert ext in reg.extractors

    def test_register_postprocessor(self):
        reg = self._fresh_registry()
        pp = _GoodPostProcessor()
        reg.register_postprocessor(pp)
        assert pp in reg.postprocessors

    def test_register_formatter(self):
        reg = self._fresh_registry()
        fmt = _GoodFormatter()
        reg.register_formatter(fmt)
        assert fmt in reg.formatters

    def test_get_extractor_by_name(self):
        reg = self._fresh_registry()
        reg.register_extractor(_GoodExtractor())
        result = reg.get_extractor("good_extractor")
        assert result is not None
        assert result.name == "good_extractor"

    def test_get_extractor_returns_none_for_unknown(self):
        reg = self._fresh_registry()
        assert reg.get_extractor("nonexistent") is None

    def test_get_postprocessor_by_name(self):
        reg = self._fresh_registry()
        reg.register_postprocessor(_GoodPostProcessor())
        result = reg.get_postprocessor("good_postprocessor")
        assert result is not None

    def test_get_formatter_by_name(self):
        reg = self._fresh_registry()
        reg.register_formatter(_GoodFormatter())
        result = reg.get_formatter("good_formatter")
        assert result is not None

    def test_summary_table_contains_all_plugins(self):
        reg = self._fresh_registry()
        reg.register_extractor(_GoodExtractor())
        reg.register_postprocessor(_GoodPostProcessor())
        reg.register_formatter(_GoodFormatter())
        table = reg.summary_table()
        types_in_table = {row["type"] for row in table}
        assert "extractor" in types_in_table
        assert "postprocessor" in types_in_table
        assert "formatter" in types_in_table

    def test_summary_table_row_keys(self):
        reg = self._fresh_registry()
        reg.register_postprocessor(_GoodPostProcessor())
        table = reg.summary_table()
        assert len(table) == 1
        row = table[0]
        assert set(row.keys()) == {"type", "name", "version", "description"}

    def test_lazy_discovery_triggered_by_property_access(self):
        reg = PluginRegistry()
        assert reg._discovered is False
        with patch("summarizer.plugins._get_entry_points", return_value=[]):
            _ = reg.extractors
        assert reg._discovered is True

    def test_discover_is_idempotent(self):
        reg = self._fresh_registry()
        reg.register_postprocessor(_GoodPostProcessor())
        with patch("summarizer.plugins._get_entry_points", return_value=[]):
            reg.discover()
        # After re-discovery the manually registered plugin should be gone
        # (discover() resets the lists from entry points)
        assert len(reg.postprocessors) == 0


# ===========================================================================
# Plugin validation
# ===========================================================================


class TestPluginValidation:
    def test_validate_rejects_wrong_base_class(self):
        reg = PluginRegistry()
        reg._discovered = True
        with pytest.raises(PluginLoadError, match="must be an instance of"):
            reg.register_extractor(_GoodPostProcessor())  # type: ignore[arg-type]

    def test_validate_rejects_missing_name(self):
        class _NoName(BasePostProcessor):
            name = ""  # empty!
            description = "test"

            def process(self, summary, original_text, **kwargs):
                return summary

        reg = PluginRegistry()
        reg._discovered = True
        with pytest.raises(PluginLoadError, match="non-empty 'name'"):
            reg.register_postprocessor(_NoName())

    def test_instantiate_and_validate_rejects_non_class(self):
        with pytest.raises(PluginLoadError, match="must point to a class"):
            _instantiate_and_validate("not_a_class", BasePostProcessor, "ep_name")

    def test_instantiate_and_validate_rejects_wrong_subclass(self):
        with pytest.raises(PluginLoadError, match="must subclass"):
            _instantiate_and_validate(_GoodExtractor, BasePostProcessor, "ep_name")

    def test_instantiate_and_validate_rejects_init_error(self):
        class _BadInit(BasePostProcessor):
            name = "bad"
            description = "raises on init"

            def __init__(self):
                raise RuntimeError("Boom!")

            def process(self, summary, original_text, **kwargs):
                return summary

        with pytest.raises(PluginLoadError, match="Failed to instantiate"):
            _instantiate_and_validate(_BadInit, BasePostProcessor, "ep_name")


# ===========================================================================
# Entry-point discovery (mocked)
# ===========================================================================


class TestEntryPointDiscovery:
    def _make_ep(self, name: str, cls: type) -> MagicMock:
        ep = MagicMock()
        ep.name = name
        ep.load.return_value = cls
        return ep

    def test_discovers_postprocessor_from_entry_point(self):
        ep = self._make_ep("good_postprocessor", _GoodPostProcessor)

        def fake_ep(group):
            if group == "summarizer.postprocessors":
                return [ep]
            return []

        reg = PluginRegistry()
        with patch("summarizer.plugins._get_entry_points", side_effect=fake_ep):
            reg.discover()

        assert len(reg.postprocessors) == 1
        assert reg.postprocessors[0].name == "good_postprocessor"

    def test_skips_entry_point_that_fails_to_load(self):
        ep = MagicMock()
        ep.name = "broken_plugin"
        ep.load.side_effect = ImportError("module not found")

        reg = PluginRegistry()
        with patch("summarizer.plugins._get_entry_points", return_value=[ep]):
            reg.discover()

        assert reg.postprocessors == []

    def test_skips_entry_point_pointing_to_non_class(self):
        ep = MagicMock()
        ep.name = "not_a_class"
        ep.load.return_value = "just_a_string"

        reg = PluginRegistry()

        def fake_ep(group):
            if group == "summarizer.postprocessors":
                return [ep]
            return []

        with patch("summarizer.plugins._get_entry_points", side_effect=fake_ep):
            reg.discover()

        assert reg.postprocessors == []

    def test_skips_entry_point_with_wrong_base_class(self):
        ep = self._make_ep("wrong_base", _GoodExtractor)  # extractor, not postprocessor

        def fake_ep(group):
            if group == "summarizer.postprocessors":
                return [ep]
            return []

        reg = PluginRegistry()
        with patch("summarizer.plugins._get_entry_points", side_effect=fake_ep):
            reg.discover()

        assert reg.postprocessors == []


# ===========================================================================
# Built-in: KeywordExtractor
# ===========================================================================


class TestKeywordExtractor:
    def test_name_and_version(self):
        ke = KeywordExtractor()
        assert ke.name == "keyword_extractor"
        assert ke.version == "1.0.0"

    def test_process_adds_keywords_to_metadata(self):
        ke = KeywordExtractor(top_n=5)
        text = (
            "Machine learning is a subset of artificial intelligence. "
            "Deep learning models use neural networks. "
            "Neural networks are inspired by the human brain. "
            "Artificial intelligence and machine learning are transforming industries."
        )
        summary = _make_summary()
        result = ke.process(summary, text)
        assert "keywords" in result.metadata
        assert isinstance(result.metadata["keywords"], list)
        assert len(result.metadata["keywords"]) <= 5

    def test_process_with_empty_text_returns_empty_list(self):
        ke = KeywordExtractor()
        summary = _make_summary()
        result = ke.process(summary, "")
        assert result.metadata["keywords"] == []

    def test_process_with_whitespace_only_returns_empty_list(self):
        ke = KeywordExtractor()
        summary = _make_summary()
        result = ke.process(summary, "   \n\t  ")
        assert result.metadata["keywords"] == []

    def test_top_n_kwarg_overrides_instance_default(self):
        ke = KeywordExtractor(top_n=10)
        text = " ".join(["word"] * 100 + ["unique"] * 5)
        summary = _make_summary()
        result = ke.process(summary, text, top_n=3)
        assert len(result.metadata["keywords"]) <= 3

    def test_initialises_metadata_if_none(self):
        ke = KeywordExtractor()
        summary = Summary(text="hello", metadata=None)
        result = ke.process(summary, "hello world test content article")
        assert result.metadata is not None
        assert "keywords" in result.metadata

    def test_returns_same_summary_object(self):
        ke = KeywordExtractor()
        summary = _make_summary()
        result = ke.process(summary, "some article text")
        assert result is summary

    def test_keywords_are_strings(self):
        ke = KeywordExtractor(top_n=5)
        summary = _make_summary()
        result = ke.process(
            summary,
            "Python programming language is widely used for data science and machine learning.",
        )
        for kw in result.metadata["keywords"]:
            assert isinstance(kw, str)

    def test_stop_words_excluded(self):
        ke = KeywordExtractor(top_n=10)
        text = "The quick brown fox jumps over the lazy dog and the fox ran away."
        summary = _make_summary()
        result = ke.process(summary, text)
        stop_words_found = [kw for kw in result.metadata["keywords"] if kw in {"the", "and", "over"}]
        assert stop_words_found == []


# ===========================================================================
# Built-in: ReadabilityScorer
# ===========================================================================


class TestReadabilityScorer:
    def test_name_and_version(self):
        rs = ReadabilityScorer()
        assert rs.name == "readability_scorer"
        assert rs.version == "1.0.0"

    def test_process_adds_readability_keys(self):
        rs = ReadabilityScorer()
        summary = _make_summary("The cat sat on the mat. It was a fat cat.")
        result = rs.process(summary, "")
        assert "readability_ease" in result.metadata
        assert "readability_grade" in result.metadata
        assert "readability_label" in result.metadata

    def test_process_ease_score_is_float_in_range(self):
        rs = ReadabilityScorer()
        summary = _make_summary("Simple text. Easy words. Short sentences.")
        result = rs.process(summary, "")
        ease = result.metadata["readability_ease"]
        assert isinstance(ease, float)
        assert 0.0 <= ease <= 100.0

    def test_process_grade_is_non_negative(self):
        rs = ReadabilityScorer()
        summary = _make_summary("Complex multisyllabic vocabulary characterises sophisticated prose.")
        result = rs.process(summary, "")
        grade = result.metadata["readability_grade"]
        assert isinstance(grade, float)
        assert grade >= 0.0

    def test_process_label_is_string(self):
        rs = ReadabilityScorer()
        summary = _make_summary("Hello world. This is a test.")
        result = rs.process(summary, "")
        assert isinstance(result.metadata["readability_label"], str)

    def test_empty_summary_text_returns_none_scores(self):
        rs = ReadabilityScorer()
        summary = _make_summary("")
        result = rs.process(summary, "")
        assert result.metadata["readability_ease"] is None
        assert result.metadata["readability_grade"] is None
        assert result.metadata["readability_label"] == "N/A"

    def test_whitespace_only_summary_returns_none_scores(self):
        rs = ReadabilityScorer()
        summary = _make_summary("   \n  ")
        result = rs.process(summary, "")
        assert result.metadata["readability_ease"] is None

    def test_initialises_metadata_if_none(self):
        rs = ReadabilityScorer()
        summary = Summary(text="A short sentence.", metadata=None)
        result = rs.process(summary, "")
        assert result.metadata is not None
        assert "readability_ease" in result.metadata

    def test_returns_same_summary_object(self):
        rs = ReadabilityScorer()
        summary = _make_summary("Hello world.")
        result = rs.process(summary, "")
        assert result is summary

    def test_original_text_not_used(self):
        """ReadabilityScorer should analyse summary.text, not original_text."""
        rs = ReadabilityScorer()
        short_summary = _make_summary("Hi. OK.")
        long_original = "This is an extremely long and complex original article " * 50
        result = rs.process(short_summary, long_original)
        # Scores should reflect the short summary, not the long original
        assert result.metadata["readability_ease"] is not None

    # ---- Internal helpers ----

    def test_count_sentences(self):
        assert _count_sentences("Hello. World. Test.") == 3
        assert _count_sentences("Hello! World? Test.") == 3
        assert _count_sentences("No terminal punctuation") == 1

    def test_count_words(self):
        assert _count_words("Hello world") == 2
        assert _count_words("one") == 1
        assert _count_words("") == 1  # returns max(1, 0) = 1

    def test_count_syllables_in_word(self):
        # Basic checks – not exhaustive (heuristic)
        assert _count_syllables_in_word("cat") >= 1
        assert _count_syllables_in_word("beautiful") >= 3
        assert _count_syllables_in_word("") == 0

    def test_ease_label_very_easy(self):
        assert _ease_label(95) == "Very Easy"

    def test_ease_label_easy(self):
        assert _ease_label(85) == "Easy"

    def test_ease_label_fairly_easy(self):
        assert _ease_label(75) == "Fairly Easy"

    def test_ease_label_standard(self):
        assert _ease_label(65) == "Standard"

    def test_ease_label_fairly_difficult(self):
        assert _ease_label(55) == "Fairly Difficult"

    def test_ease_label_difficult(self):
        assert _ease_label(40) == "Difficult"

    def test_ease_label_very_difficult(self):
        assert _ease_label(10) == "Very Difficult"

    def test_flesch_kincaid_returns_tuple(self):
        ease, grade = _flesch_kincaid("The cat sat on the mat.")
        assert isinstance(ease, float)
        assert isinstance(grade, float)

    def test_flesch_kincaid_simple_text_has_high_ease(self):
        ease, _ = _flesch_kincaid("The cat sat. The dog ran. The bird flew.")
        assert ease >= 50  # should be relatively easy

    def test_flesch_kincaid_complex_text_has_lower_ease(self):
        complex_text = (
            "The epistemological ramifications of poststructuralist hermeneutics "
            "necessitate a comprehensive recontextualisation of interdisciplinary "
            "methodological paradigms within contemporary philosophical discourse."
        )
        ease, _ = _flesch_kincaid(complex_text)
        simple_ease, _ = _flesch_kincaid("The cat sat on the mat.")
        assert ease < simple_ease


# ===========================================================================
# CLI: plugins list
# ===========================================================================


class TestCLIPluginsList:
    def test_plugins_list_exits_zero(self, capsys):
        from summarizer.cli import main

        with patch("summarizer.plugins._get_entry_points", return_value=[]):
            exit_code = main(["plugins", "list"])

        assert exit_code == 0

    def test_plugins_list_shows_no_plugins_message_when_empty(self, capsys):
        from summarizer.cli import main

        with patch("summarizer.plugins._get_entry_points", return_value=[]):
            main(["plugins", "list"])

        captured = capsys.readouterr()
        assert "No plugins discovered" in captured.out

    def test_plugins_list_shows_registered_plugin(self, capsys):
        from summarizer.cli import cmd_plugins_list, registry
        import argparse

        # Reset and repopulate the global registry
        reg_backup_extractors = list(registry._extractors)
        reg_backup_postprocessors = list(registry._postprocessors)
        reg_backup_formatters = list(registry._formatters)

        try:
            with patch("summarizer.plugins._get_entry_points", return_value=[]):
                registry.discover()
            registry.register_postprocessor(_GoodPostProcessor())

            with patch("summarizer.plugins._get_entry_points", return_value=[]):
                # Patch discover to not wipe out our manual registration
                original_discover = registry.discover

                def _patched_discover():
                    pass  # no-op

                registry.discover = _patched_discover  # type: ignore[method-assign]
                cmd_plugins_list(argparse.Namespace())
                registry.discover = original_discover  # type: ignore[method-assign]

            captured = capsys.readouterr()
            assert "good_postprocessor" in captured.out
        finally:
            registry._extractors = reg_backup_extractors
            registry._postprocessors = reg_backup_postprocessors
            registry._formatters = reg_backup_formatters

    def test_plugins_list_unknown_command_exits_nonzero(self):
        from summarizer.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["plugins", "nonexistent"])

        assert exc_info.value.code != 0


# ===========================================================================
# CLI: run with post-processors
# ===========================================================================


class TestCLIRunWithPostProcessors:
    def test_run_applies_postprocessors(self, capsys):
        from summarizer.cli import main
        from summarizer.plugins import registry

        class _TaggingProcessor(_GoodPostProcessor):
            name = "tagging_processor"

            def process(self, summary, original_text, **kwargs):
                summary.text += " [TAGGED]"
                return summary

        reg_backup = list(registry._postprocessors)
        try:
            with patch("summarizer.plugins._get_entry_points", return_value=[]):
                registry.discover()
            registry.register_postprocessor(_TaggingProcessor())

            def _no_op_discover():
                pass

            registry.discover = _no_op_discover  # type: ignore[method-assign]
            main(["run", "--text", "Hello world article."])
            del registry.discover  # restore to class method

            captured = capsys.readouterr()
            assert "[TAGGED]" in captured.out
        finally:
            registry._postprocessors = reg_backup

    def test_run_warns_on_postprocessor_failure(self, capsys):
        from summarizer.cli import main
        from summarizer.plugins import registry

        class _FailingProcessor(BasePostProcessor):
            name = "failing_processor"
            description = "always fails"

            def process(self, summary, original_text, **kwargs):
                raise RuntimeError("intentional failure")

        reg_backup = list(registry._postprocessors)
        try:
            with patch("summarizer.plugins._get_entry_points", return_value=[]):
                registry.discover()
            registry.register_postprocessor(_FailingProcessor())

            def _no_op_discover():
                pass

            registry.discover = _no_op_discover  # type: ignore[method-assign]
            exit_code = main(["run", "--text", "Some article text."])
            del registry.discover

            captured = capsys.readouterr()
            assert "warning" in captured.err.lower()
            assert exit_code == 0  # overall run still succeeds
        finally:
            registry._postprocessors = reg_backup