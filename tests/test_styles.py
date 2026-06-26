"""Tests verifying that each SummaryStyle generates a distinctly different prompt."""

import pytest

from src.summarizer.llm.prompts import PROMPT_TEMPLATES, get_prompt
from src.summarizer.styles import STYLE_PROMPT_MAP, SummaryStyle


SAMPLE_TEXT = "Artificial intelligence is transforming many industries."


class TestSummaryStyleEnum:
    """Tests for the SummaryStyle enum."""

    def test_all_styles_defined(self):
        """Ensure all expected styles are present."""
        expected = {"bullets", "brief", "detailed", "eli5", "tldr"}
        actual = {s.value for s in SummaryStyle}
        assert actual == expected

    def test_style_values_are_strings(self):
        for style in SummaryStyle:
            assert isinstance(style.value, str)

    def test_style_map_covers_all_styles(self):
        """Every SummaryStyle must have a corresponding prompt key."""
        for style in SummaryStyle:
            assert style in STYLE_PROMPT_MAP, f"{style} not in STYLE_PROMPT_MAP"

    def test_style_map_keys_exist_in_prompts(self):
        """Every mapped prompt key must exist in PROMPT_TEMPLATES."""
        for style, key in STYLE_PROMPT_MAP.items():
            assert key in PROMPT_TEMPLATES, (
                f"Style {style} maps to key '{key}' which is missing from PROMPT_TEMPLATES"
            )


class TestPromptTemplates:
    """Tests verifying prompt template content and distinctiveness."""

    def test_all_templates_present(self):
        required_keys = {"brief", "bullets", "detailed", "eli5", "tldr"}
        assert required_keys.issubset(set(PROMPT_TEMPLATES.keys()))

    def test_all_templates_are_strings(self):
        for key, template in PROMPT_TEMPLATES.items():
            assert isinstance(template, str), f"Template '{key}' is not a string"

    def test_all_templates_contain_text_placeholder(self):
        for key, template in PROMPT_TEMPLATES.items():
            assert "{text}" in template, (
                f"Template '{key}' is missing the {{text}} placeholder"
            )

    def test_templates_are_distinct(self):
        """Each template must differ from all others."""
        keys = list(PROMPT_TEMPLATES.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                assert PROMPT_TEMPLATES[keys[i]] != PROMPT_TEMPLATES[keys[j]], (
                    f"Templates '{keys[i]}' and '{keys[j]}' are identical"
                )

    def test_brief_template_mentions_concise(self):
        assert any(
            word in PROMPT_TEMPLATES["brief"].lower()
            for word in ["concise", "brief", "short", "2-4", "sentences"]
        )

    def test_bullets_template_mentions_bullet(self):
        assert any(
            word in PROMPT_TEMPLATES["bullets"].lower()
            for word in ["bullet", "list", "points", "-"]
        )

    def test_detailed_template_mentions_comprehensive(self):
        assert any(
            word in PROMPT_TEMPLATES["detailed"].lower()
            for word in ["comprehensive", "detailed", "thorough", "all major"]
        )

    def test_eli5_template_mentions_simple_language(self):
        assert any(
            word in PROMPT_TEMPLATES["eli5"].lower()
            for word in ["simple", "10-year-old", "child", "easy", "jargon"]
        )

    def test_tldr_template_mentions_short(self):
        assert any(
            word in PROMPT_TEMPLATES["tldr"].lower()
            for word in ["tl;dr", "short", "brief", "1-2", "ultra"]
        )


class TestGetPrompt:
    """Tests for the get_prompt helper function."""

    def test_get_prompt_inserts_text(self):
        for style in SummaryStyle:
            key = STYLE_PROMPT_MAP[style]
            result = get_prompt(key, SAMPLE_TEXT)
            assert SAMPLE_TEXT in result, (
                f"Text not found in prompt for style '{key}'"
            )

    def test_get_prompt_returns_string(self):
        for style in SummaryStyle:
            key = STYLE_PROMPT_MAP[style]
            result = get_prompt(key, SAMPLE_TEXT)
            assert isinstance(result, str)

    def test_get_prompt_invalid_key_raises(self):
        with pytest.raises(KeyError, match="Unknown style key"):
            get_prompt("nonexistent_style", SAMPLE_TEXT)

    def test_prompts_differ_across_styles(self):
        """Prompts for different styles must not be identical."""
        results = {}
        for style in SummaryStyle:
            key = STYLE_PROMPT_MAP[style]
            results[style] = get_prompt(key, SAMPLE_TEXT)

        style_list = list(results.keys())
        for i in range(len(style_list)):
            for j in range(i + 1, len(style_list)):
                s1, s2 = style_list[i], style_list[j]
                assert results[s1] != results[s2], (
                    f"Prompts for {s1} and {s2} are identical"
                )

    def test_prompt_length_varies_by_style(self):
        """Different styles should produce different-length prompts (excluding text)."""
        template_lengths = {
            key: len(template.replace("{text}", ""))
            for key, template in PROMPT_TEMPLATES.items()
        }
        unique_lengths = set(template_lengths.values())
        # At least some styles should have different template lengths
        assert len(unique_lengths) > 1, "All prompt templates have identical lengths"