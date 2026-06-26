"""Tests for SummaryStyle prompt generation."""

import pytest

from src.summarizer.styles import SummaryStyle
from src.summarizer.llm.prompts import get_prompt, STYLE_PROMPTS


SAMPLE_TEXT = (
    "Scientists announced today that they have developed a new battery technology "
    "that can charge a smartphone in under 60 seconds and lasts twice as long as "
    "current lithium-ion batteries. The breakthrough uses a novel graphene-based "
    "anode material and is expected to reach consumer devices within three years."
)


class TestSummaryStyleCoverage:
    """Every SummaryStyle must have a registered prompt template."""

    def test_all_styles_have_prompts(self):
        for style in SummaryStyle:
            assert style in STYLE_PROMPTS, (
                f"SummaryStyle.{style.name} has no entry in STYLE_PROMPTS"
            )

    def test_all_templates_have_system_key(self):
        for style, template in STYLE_PROMPTS.items():
            assert "system" in template, (
                f"Template for {style.name} is missing 'system' key"
            )

    def test_all_templates_have_user_prefix_key(self):
        for style, template in STYLE_PROMPTS.items():
            assert "user_prefix" in template, (
                f"Template for {style.name} is missing 'user_prefix' key"
            )


class TestGetPrompt:
    """get_prompt() should return correctly structured dicts."""

    @pytest.mark.parametrize("style", list(SummaryStyle))
    def test_returns_system_and_user_keys(self, style):
        result = get_prompt(style, SAMPLE_TEXT)
        assert "system" in result
        assert "user" in result

    @pytest.mark.parametrize("style", list(SummaryStyle))
    def test_user_contains_article_text(self, style):
        result = get_prompt(style, SAMPLE_TEXT)
        assert SAMPLE_TEXT in result["user"]

    @pytest.mark.parametrize("style", list(SummaryStyle))
    def test_system_is_non_empty_string(self, style):
        result = get_prompt(style, SAMPLE_TEXT)
        assert isinstance(result["system"], str)
        assert len(result["system"]) > 20

    def test_raises_for_unknown_style(self):
        """get_prompt should raise ValueError for unrecognised styles."""
        # Simulate an unregistered style by temporarily removing one
        from src.summarizer.llm import prompts

        original = dict(prompts.STYLE_PROMPTS)
        prompts.STYLE_PROMPTS.clear()
        try:
            with pytest.raises(ValueError, match="No prompt template"):
                get_prompt(SummaryStyle.BRIEF, SAMPLE_TEXT)
        finally:
            prompts.STYLE_PROMPTS.update(original)


class TestPromptsAreDistinct:
    """Each SummaryStyle should produce a distinctly different prompt."""

    def test_system_prompts_are_unique(self):
        system_prompts = [
            get_prompt(style, SAMPLE_TEXT)["system"] for style in SummaryStyle
        ]
        assert len(system_prompts) == len(set(system_prompts)), (
            "Two or more SummaryStyle values share an identical system prompt"
        )

    def test_user_prefixes_are_unique(self):
        prefixes = [
            STYLE_PROMPTS[style]["user_prefix"] for style in SummaryStyle
        ]
        assert len(prefixes) == len(set(prefixes)), (
            "Two or more SummaryStyle values share an identical user_prefix"
        )

    def test_brief_mentions_executive(self):
        prompt = get_prompt(SummaryStyle.BRIEF, SAMPLE_TEXT)
        assert "executive" in prompt["system"].lower()

    def test_bullets_mentions_bullet(self):
        prompt = get_prompt(SummaryStyle.BULLETS, SAMPLE_TEXT)
        combined = (prompt["system"] + prompt["user"]).lower()
        assert "bullet" in combined

    def test_detailed_mentions_comprehensive_or_detailed(self):
        prompt = get_prompt(SummaryStyle.DETAILED, SAMPLE_TEXT)
        combined = (prompt["system"] + prompt["user"]).lower()
        assert "comprehensive" in combined or "detailed" in combined

    def test_eli5_mentions_simple_or_child(self):
        prompt = get_prompt(SummaryStyle.ELI5, SAMPLE_TEXT)
        combined = (prompt["system"] + prompt["user"]).lower()
        assert "simple" in combined or "child" in combined or "10-year" in combined

    def test_tldr_mentions_tldr_or_sentence(self):
        prompt = get_prompt(SummaryStyle.TLDR, SAMPLE_TEXT)
        combined = (prompt["system"] + prompt["user"]).lower()
        assert "tl;dr" in combined or "tldr" in combined or "sentence" in combined