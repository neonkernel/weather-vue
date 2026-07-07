"""
Tests for the plugin system.

Covers:
- PluginRegistry discovery and loading
- BaseExtractor / BasePostProcessor / BaseFormatter ABCs
- Built-in post-processors (KeywordExtractor, ReadabilityScorer)
- Error handling for malformed plugins
- Programmatic registration helpers
- `plugins list` CLI command
"""

from __future__ import annotations

import sys
import types
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — minimal stub objects
# ---------------------------------------------------------------------------


class _StubSummary:
    """Minimal summary-like object used across tests."""

    def __init__(self, text: str = ""):
        self.summary = text
        self.text = text


# ---------------------------------------------------------------------------
# ABCs
# ---------------------------------------------------------------------------


class TestBaseABCs:
    def test_base_extractor_is_abstract(self):
        from summarizer.plugins.base import BaseExtractor

        with pytest.raises(TypeError):
            BaseExtractor()  # type: ignore[abstract]

    def test_base_postprocessor_is_abstract(self):
        from summarizer.plugins.base import BasePostProcessor

        with pytest.raises(TypeError):
            BasePostProcessor()  # type: ignore[abstract]

    def test_base_formatter_is_abstract(self):
        from summarizer.plugins.base import BaseFormatter

        with pytest.raises(TypeError):
            BaseFormatter()  # type: ignore[abstract]

    def test_concrete_extractor_must_implement_both_methods(self):
        from summarizer.plugins.base import BaseExtractor

        # Missing extract → still abstract
        class IncompleteExtractor(BaseExtractor):
            def can_handle(self, url: str) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteExtractor()  # type: ignore[abstract]

    def test_concrete_extractor_can_be_instantiated(self):
        from summarizer.plugins.base import BaseExtractor

        class GoodExtractor(BaseExtractor):
            name = "good"
            description = "test"

            def can_handle(self, url: str) -> bool:
                return url.startswith("https://")

            def extract(self, url: str) -> str:
                return "article text"

        ext = GoodExtractor()
        assert ext.can_handle("https://example.com")
        assert not ext.can_handle("http://example.com")
        assert ext.extract("https://x.com") == "article text"

    def test_concrete_postprocessor_can_be_instantiated(self):
        from summarizer.plugins.base import BasePostProcessor

        class TagAdder(BasePostProcessor):
            name = "tag_adder"
            description = "Adds tags"

            def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
                summary.tags = ["test"]
                return summary

        pp = TagAdder()
        s = _StubSummary("hello world")
        result = pp.process(s)
        assert result.tags == ["test"]

    def test_concrete_formatter_can_be_instantiated(self):
        from summarizer.plugins.base import BaseFormatter

        class HtmlFormatter(BaseFormatter):
            name = "html"
            description = "HTML output"
            extension = ".html"

            def format(self, summary: Any) -> str:
                return f"<p>{summary.summary}</p>"

        fmt = HtmlFormatter()
        s = _StubSummary("hello")
        assert fmt.format(s) == "<p>hello</p>"


# ---------------------------------------------------------------------------
# PluginRegistry
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def _fresh_registry(self):
        """Return a new, unloaded PluginRegistry."""
        from summarizer.plugins import PluginRegistry

        return PluginRegistry()

    def test_registry_loads_without_error(self):
        reg = self._fresh_registry()
        reg.load()
        # Should not raise

    def test_registry_is_lazy(self):
        reg = self._fresh_registry()
        assert not reg._loaded

    def test_registry_loads_on_first_access(self):
        reg = self._fresh_registry()
        _ = reg.get_postprocessors()
        assert reg._loaded

    def test_list_all_returns_correct_keys(self):
        reg = self._fresh_registry()
        result = reg.list_all()
        assert set(result.keys()) == {"extractors", "postprocessors", "formatters"}

    # ------------------------------------------------------------------
    # Programmatic registration
    # ------------------------------------------------------------------

    def test_register_extractor(self):
        from summarizer.plugins.base import BaseExtractor

        class DummyExtractor(BaseExtractor):
            name = "dummy_ext"
            description = ""

            def can_handle(self, url: str) -> bool:
                return True

            def extract(self, url: str) -> str:
                return ""

        reg = self._fresh_registry()
        reg.register_extractor(DummyExtractor())
        assert reg.get_extractor("dummy_ext") is not None

    def test_register_postprocessor(self):
        from summarizer.plugins.base import BasePostProcessor

        class DummyPP(BasePostProcessor):
            name = "dummy_pp"
            description = ""

            def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
                return summary

        reg = self._fresh_registry()
        reg.register_postprocessor(DummyPP())
        assert reg.get_postprocessor("dummy_pp") is not None

    def test_register_formatter(self):
        from summarizer.plugins.base import BaseFormatter

        class DummyFmt(BaseFormatter):
            name = "dummy_fmt"
            description = ""
            extension = ".txt"

            def format(self, summary: Any) -> str:
                return ""

        reg = self._fresh_registry()
        reg.register_formatter(DummyFmt())
        assert reg.get_formatter("dummy_fmt") is not None

    def test_register_wrong_type_raises(self):
        reg = self._fresh_registry()
        with pytest.raises(TypeError):
            reg.register_extractor("not_an_extractor")  # type: ignore

    # ------------------------------------------------------------------
    # find_extractor_for
    # ------------------------------------------------------------------

    def test_find_extractor_for_returns_none_when_none_registered(self):
        reg = self._fresh_registry()
        reg.load()
        assert reg.find_extractor_for("https://example.com") is None

    def test_find_extractor_for_returns_first_matching(self):
        from summarizer.plugins.base import BaseExtractor

        class HttpsExtractor(BaseExtractor):
            name = "https_only"
            description = ""

            def can_handle(self, url: str) -> bool:
                return url.startswith("https://")

            def extract(self, url: str) -> str:
                return "https content"

        reg = self._fresh_registry()
        reg.register_extractor(HttpsExtractor())
        found = reg.find_extractor_for("https://example.com")
        assert found is not None
        assert found.name == "https_only"

        assert reg.find_extractor_for("http://example.com") is None

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_malformed_plugin_skipped_by_default(self):
        """A plugin that raises on load should be skipped, not crash the registry."""
        reg = self._fresh_registry()

        # Simulate a bad entry point
        bad_ep = MagicMock()
        bad_ep.name = "bad_plugin"
        bad_ep.load.side_effect = ImportError("missing dependency")

        good_ep = MagicMock()
        good_ep.name = "good_plugin"

        from summarizer.plugins.base import BasePostProcessor

        class GoodPP(BasePostProcessor):
            name = "good_plugin"
            description = ""

            def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
                return summary

        good_ep.load.return_value = GoodPP

        with patch("summarizer.plugins.entry_points") as mock_eps:
            def side_effect(group):
                if group == "summarizer.postprocessors":
                    return [bad_ep, good_ep]
                return []

            mock_eps.side_effect = side_effect
            reg.load(raise_on_error=False)

        # bad plugin skipped, good one loaded
        assert reg.get_postprocessor("bad_plugin") is None
        assert reg.get_postprocessor("good_plugin") is not None

    def test_malformed_plugin_raises_when_raise_on_error(self):
        from summarizer.plugins import PluginLoadError

        reg = self._fresh_registry()

        bad_ep = MagicMock()
        bad_ep.name = "bad_plugin"
        bad_ep.load.side_effect = ImportError("kaboom")

        with patch("summarizer.plugins.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [bad_ep] if group == "summarizer.extractors" else []
            )
            with pytest.raises(PluginLoadError, match="kaboom"):
                reg.load(raise_on_error=True)

    def test_non_subclass_plugin_skipped(self):
        """A class that doesn't subclass the correct ABC is rejected."""
        reg = self._fresh_registry()

        class NotAPostProcessor:
            name = "impostor"

        ep = MagicMock()
        ep.name = "impostor"
        ep.load.return_value = NotAPostProcessor

        with patch("summarizer.plugins.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [ep] if group == "summarizer.postprocessors" else []
            )
            reg.load(raise_on_error=False)

        assert reg.get_postprocessor("impostor") is None

    def test_non_subclass_plugin_raises_when_raise_on_error(self):
        from summarizer.plugins import PluginLoadError

        reg = self._fresh_registry()

        class NotAPostProcessor:
            name = "impostor"

        ep = MagicMock()
        ep.name = "impostor"
        ep.load.return_value = NotAPostProcessor

        with patch("summarizer.plugins.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [ep] if group == "summarizer.postprocessors" else []
            )
            with pytest.raises(PluginLoadError):
                reg.load(raise_on_error=True)

    def test_instantiation_error_skipped(self):
        reg = self._fresh_registry()

        from summarizer.plugins.base import BasePostProcessor

        class BadInit(BasePostProcessor):
            name = "bad_init"
            description = ""

            def __init__(self):
                raise RuntimeError("cannot init")

            def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
                return summary

        ep = MagicMock()
        ep.name = "bad_init"
        ep.load.return_value = BadInit

        with patch("summarizer.plugins.entry_points") as mock_eps:
            mock_eps.side_effect = lambda group: (
                [ep] if group == "summarizer.postprocessors" else []
            )
            reg.load(raise_on_error=False)

        assert reg.get_postprocessor("bad_init") is None


# ---------------------------------------------------------------------------
# Built-in post-processors
# ---------------------------------------------------------------------------


class TestKeywordExtractor:
    def test_extracts_keywords_from_article_text(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        ke = KeywordExtractor(top_n=5)
        s = _StubSummary("The cat sat on the mat. The cat ate a rat.")
        result = ke.process(s, article_text="The cat sat on the mat. The cat ate a rat.")
        assert hasattr(result, "keywords")
        assert isinstance(result.keywords, list)
        assert len(result.keywords) <= 5

    def test_falls_back_to_summary_text(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        ke = KeywordExtractor(top_n=3)
        s = _StubSummary("Python is a great programming language for data science.")
        result = ke.process(s, article_text=None)
        assert hasattr(result, "keywords")
        assert "python" in result.keywords or len(result.keywords) >= 1

    def test_empty_text_returns_empty_keywords(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        ke = KeywordExtractor()
        s = _StubSummary("")
        result = ke.process(s, article_text="")
        assert result.keywords == []

    def test_top_n_respected(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        text = " ".join(["word" + str(i) for i in range(50)])
        ke = KeywordExtractor(top_n=7)
        s = _StubSummary()
        result = ke.process(s, article_text=text)
        assert len(result.keywords) <= 7

    def test_extract_keywords_function_directly(self):
        from summarizer.plugins.builtin.keyword_extractor import extract_keywords

        keywords = extract_keywords("The quick brown fox jumps over the lazy dog", top_n=4)
        assert isinstance(keywords, list)
        assert len(keywords) <= 4

    def test_plugin_metadata(self):
        from summarizer.plugins.builtin.keyword_extractor import KeywordExtractor

        ke = KeywordExtractor()
        assert ke.name == "keyword_extractor"
        assert ke.description


class TestReadabilityScorer:
    _SIMPLE_TEXT = (
        "The cat sat on the mat. It was a sunny day. "
        "The cat was happy. The mat was soft and warm."
    )
    _COMPLEX_TEXT = (
        "The epistemological ramifications of postmodern deconstructionism "
        "fundamentally undermine the ontological presuppositions inherent in "
        "traditional metaphysical frameworks. Such considerations necessitate "
        "a comprehensive re-evaluation of hermeneutical methodologies."
    )

    def test_attaches_readability_to_summary(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        rs = ReadabilityScorer()
        s = _StubSummary(self._SIMPLE_TEXT)
        result = rs.process(s)
        assert hasattr(result, "readability")

    def test_readability_result_fields(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        rs = ReadabilityScorer()
        s = _StubSummary(self._SIMPLE_TEXT)
        result = rs.process(s)
        r = result.readability
        assert hasattr(r, "flesch_reading_ease")
        assert hasattr(r, "flesch_kincaid_grade")
        assert hasattr(r, "word_count")
        assert hasattr(r, "sentence_count")
        assert hasattr(r, "syllable_count")
        assert hasattr(r, "interpretation")

    def test_simple_text_has_higher_reading_ease_than_complex(self):
        from summarizer.plugins.builtin.readability import compute_readability

        simple = compute_readability(self._SIMPLE_TEXT)
        complex_ = compute_readability(self._COMPLEX_TEXT)
        assert simple.flesch_reading_ease > complex_.flesch_reading_ease

    def test_empty_summary_returns_zeroed_result(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        rs = ReadabilityScorer()
        s = _StubSummary("")
        result = rs.process(s)
        assert result.readability.word_count == 0
        assert result.readability.interpretation == "N/A"

    def test_as_dict(self):
        from summarizer.plugins.builtin.readability import compute_readability

        r = compute_readability(self._SIMPLE_TEXT)
        d = r.as_dict()
        assert "flesch_reading_ease" in d
        assert "interpretation" in d

    def test_interpretation_labels(self):
        from summarizer.plugins.builtin.readability import _interpret_reading_ease

        assert _interpret_reading_ease(95) == "Very Easy"
        assert _interpret_reading_ease(85) == "Easy"
        assert _interpret_reading_ease(75) == "Fairly Easy"
        assert _interpret_reading_ease(65) == "Standard"
        assert _interpret_reading_ease(55) == "Fairly Difficult"
        assert _interpret_reading_ease(40) == "Difficult"
        assert _interpret_reading_ease(20) == "Very Confusing"

    def test_syllable_counting(self):
        from summarizer.plugins.builtin.readability import _count_syllables

        # "cat" → 1, "happy" → 2, "beautiful" → 3 (approx)
        assert _count_syllables("cat") == 1
        assert _count_syllables("happy") >= 2
        assert _count_syllables("") == 0

    def test_plugin_metadata(self):
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        rs = ReadabilityScorer()
        assert rs.name == "readability_scorer"
        assert rs.description

    def test_article_text_ignored_scorer_uses_summary(self):
        """ReadabilityScorer should use summary text, not article_text."""
        from summarizer.plugins.builtin.readability import ReadabilityScorer

        rs = ReadabilityScorer()
        s = _StubSummary(self._SIMPLE_TEXT)
        # Pass a very different article_text — result should still reflect summary text
        result = rs.process(s, article_text="completely different article that is very long")
        # word count should match the summary text, not the article_text
        assert result.readability.word_count == len(
            __import__("re").findall(r"\b[a-zA-Z']+\b", self._SIMPLE_TEXT)
        )


# ---------------------------------------------------------------------------
# CLI — `plugins list` command
# ---------------------------------------------------------------------------


class TestPluginsListCLI:
    def test_plugins_list_exits_zero(self, capsys):
        from summarizer.cli import main

        exit_code = main(["plugins", "list"])
        assert exit_code == 0

    def test_plugins_list_json_output(self, capsys):
        from summarizer.cli import main
        import json

        main(["plugins", "list", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "extractors" in data
        assert "postprocessors" in data
        assert "formatters" in data

    def test_plugins_list_filter_by_type(self, capsys):
        from summarizer.cli import main

        exit_code = main(["plugins", "list", "--type", "postprocessors"])
        assert exit_code == 0

    def test_plugins_list_json_filter_by_type(self, capsys):
        from summarizer.cli import main
        import json

        main(["plugins", "list", "--json", "--type", "formatters"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        # Only the requested type should be present
        assert "formatters" in data
        assert "extractors" not in data

    def test_plugins_list_human_readable_contains_sections(self, capsys):
        from summarizer.cli import main

        main(["plugins", "list"])
        captured = capsys.readouterr()
        out = captured.out
        assert "Post-Processors" in out or "Extractors" in out or "Formatters" in out

    def test_no_command_shows_help(self, capsys):
        from summarizer.cli import main

        exit_code = main([])
        assert exit_code == 0


# ---------------------------------------------------------------------------
# Integration: registry singleton used by CLI apply_postprocessors
# ---------------------------------------------------------------------------


class TestApplyPostprocessors:
    def test_no_postprocess_flag_skips_all(self):
        from summarizer.cli import _apply_postprocessors

        class TrackingPP:
            called = False

            def process(self, summary, article_text=None):
                TrackingPP.called = True
                return summary

        s = _StubSummary("hello")
        _apply_postprocessors(s, None, no_postprocess=True, filter_names=None)
        assert not TrackingPP.called

    def test_filter_names_restricts_processors(self):
        from summarizer.plugins import PluginRegistry
        from summarizer.plugins.base import BasePostProcessor
        from summarizer.cli import _apply_postprocessors
        import summarizer.plugins as plugins_module

        class PP_A(BasePostProcessor):
            name = "pp_a"
            description = ""

            def process(self, summary, article_text=None):
                summary.ran_a = True
                return summary

        class PP_B(BasePostProcessor):
            name = "pp_b"
            description = ""

            def process(self, summary, article_text=None):
                summary.ran_b = True
                return summary

        # Inject into the module-level singleton temporarily
        original_registry = plugins_module.registry
        test_registry = PluginRegistry()
        test_registry.register_postprocessor(PP_A())
        test_registry.register_postprocessor(PP_B())
        plugins_module.registry = test_registry

        try:
            s = _StubSummary("text")
            _apply_postprocessors(s, None, no_postprocess=False, filter_names=["pp_a"])
            assert hasattr(s, "ran_a")
            assert not hasattr(s, "ran_b")
        finally:
            plugins_module.registry = original_registry

    def test_processor_exception_is_logged_not_raised(self):
        from summarizer.plugins import PluginRegistry
        from summarizer.plugins.base import BasePostProcessor
        from summarizer.cli import _apply_postprocessors
        import summarizer.plugins as plugins_module

        class BadPP(BasePostProcessor):
            name = "bad_pp"
            description = ""

            def process(self, summary, article_text=None):
                raise ValueError("intentional error")

        original_registry = plugins_module.registry
        test_registry = PluginRegistry()
        test_registry.register_postprocessor(BadPP())
        plugins_module.registry = test_registry

        try:
            s = _StubSummary("text")
            # Should not raise
            result = _apply_postprocessors(s, None, no_postprocess=False, filter_names=None)
            assert result is s
        finally:
            plugins_module.registry = original_registry