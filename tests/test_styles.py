"""Tests verifying that each SummaryStyle generates a distinctly different prompt."""

import pytest

from src.summarizer.styles import SummaryStyle, STYLE_PROMPT_KEYS
from src.summarizer.llm.prompts import get_prompt, PROMPT_TEMPLATES, SYSTEM_PROMPT

SAMPLE_TEXT = (
    "Researchers at the university have discovered a new species of deep-sea fish "
    "that can produce its own light using a biochemical process never seen before. "
    "The discovery was published in the journal Nature and has excited marine biologists "
    "around the world. The fish, found at a depth of 3,000 metres, uses the light to "
    "attract prey in the otherwise pitch-black environment."
)


class TestSummaryStyleEnum:
    """Tests for the SummaryStyle enum itself."""

    def test_all_styles_defined(self):
        """All expected style values are present."""
        expected = {"bullets", "brief", "detailed", "eli5", "tldr"}
        actual = {s.value for s in SummaryStyle}
        assert actual == expected

    def test_each_style_has_prompt_key(self):
        """Every SummaryStyle has an entry in STYLE_PROMPT_KEYS."""
        for style in SummaryStyle:
            assert style in STYLE_PROMPT_KEYS, f"{style} missing from STYLE_PROMPT_KEYS"

    def test_each_style_key_has_template(self):
        """Every style key maps to an existing prompt template."""
        for style in SummaryStyle:
            key = STYLE_PROMPT_KEYS[style]
            assert key in PROMPT_TEMPLATES, (
                f"Style {style} maps to key '{key}' which is missing from PROMPT_TEMPLATES"
            )


class TestPromptTemplates:
    """Tests verifying that each style produces a distinct, non-trivial prompt."""

    def _get_rendered(self, style: SummaryStyle) -> str:
        key = STYLE_PROMPT_KEYS[style]
        return get_prompt(key, SAMPLE_TEXT)

    def test_all_prompts_contain_source_text(self):
        """Every rendered prompt contains the source text."""
        for style in SummaryStyle:
            rendered = self._get_rendered(style)
            assert SAMPLE_TEXT in rendered, (
                f"Prompt for {style} does not contain the source text"
            )

    def test_all_prompts_are_distinct(self):
        """Each style produces a different prompt (no two are identical)."""
        rendered = [self._get_rendered(style) for style in SummaryStyle]
        # Compare every pair
        for i, a in enumerate(rendered):
            for j, b in enumerate(rendered):
                if i != j:
                    assert a != b, (
                        f"Prompts for {list(SummaryStyle)[i]} and "
                        f"{list(SummaryStyle)[j]} are identical"
                    )

    def test_bullets_prompt_mentions_bullet(self):
        """Bullets style prompt instructs the model to use bullet points."""
        rendered = self._get_rendered(SummaryStyle.BULLETS)
        assert "bullet" in rendered.lower()

    def test_brief_prompt_mentions_executive(self):
        """Brief style prompt uses executive-brief language."""
        rendered = self._get_rendered(SummaryStyle.BRIEF)
        assert "executive" in rendered.lower() or "brief" in rendered.lower()

    def test_detailed_prompt_mentions_comprehensive(self):
        """Detailed style prompt requests a comprehensive summary."""
        rendered = self._get_rendered(SummaryStyle.DETAILED)
        assert "comprehensive" in rendered.lower() or "detailed" in rendered.lower()

    def test_eli5_prompt_mentions_simple_language(self):
        """ELI5 style prompt requests simple / child-friendly language."""
        rendered = self._get_rendered(SummaryStyle.ELI5)
        assert "5" in rendered or "child" in rendered.lower() or "simple" in rendered.lower()

    def test_tldr_prompt_mentions_single_sentence(self):
        """TLDR style prompt requests a single-sentence summary."""
        rendered = self._get_rendered(SummaryStyle.TLDR)
        assert "sentence" in rendered.lower() or "tl;dr" in rendered.lower()

    def test_get_prompt_raises_on_unknown_key(self):
        """get_prompt raises KeyError for an unrecognised style key."""
        with pytest.raises(KeyError, match="Unknown style key"):
            get_prompt("nonexistent_style", SAMPLE_TEXT)

    def test_system_prompt_is_non_empty(self):
        """The shared system prompt is a non-empty string."""
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 20