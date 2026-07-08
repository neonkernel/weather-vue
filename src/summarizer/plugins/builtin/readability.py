"""
Built-in post-processor: computes a Flesch-Kincaid readability score for
the summary text and attaches it to ``summary.metadata["readability"]``.

No external dependencies are required — the Flesch Reading Ease and
Flesch-Kincaid Grade Level formulas are implemented in pure Python.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from summarizer.models import Summary
from summarizer.plugins.base import BasePostProcessor


# ---------------------------------------------------------------------------
# Syllable counting (rule-based, handles most English words well)
# ---------------------------------------------------------------------------

_VOWELS = re.compile(r"[aeiouy]+", re.IGNORECASE)
_SILENT_E = re.compile(r"[^aeiouy]e$", re.IGNORECASE)
_SPECIAL = re.compile(
    r"(tion|sion|cia|tia|gion)$", re.IGNORECASE
)


def _count_syllables(word: str) -> int:
    """
    Estimate the number of syllables in an English word.

    Uses a heuristic approach that handles most common cases:
    - Count vowel groups
    - Subtract silent trailing 'e'
    - Ensure at least 1 syllable per word

    Args:
        word: A single English word (may contain punctuation at edges).

    Returns:
        Estimated syllable count (>= 1).
    """
    word = re.sub(r"[^a-zA-Z]", "", word)
    if not word:
        return 0

    count = len(_VOWELS.findall(word))
    if _SILENT_E.search(word):
        count -= 1

    return max(1, count)


def _tokenise_sentences(text: str) -> List[str]:
    """Split *text* into sentences using simple punctuation heuristics."""
    # Split on ., !, ? followed by whitespace or end-of-string
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s.strip()]


def _tokenise_words(text: str) -> List[str]:
    """Split *text* into word tokens (alphabetic only)."""
    return re.findall(r"[a-zA-Z']+", text)


# ---------------------------------------------------------------------------
# Readability formulas
# ---------------------------------------------------------------------------

def flesch_reading_ease(text: str) -> float:
    """
    Compute the Flesch Reading Ease score for *text*.

    Score interpretation:
        90-100  Very Easy
        80-90   Easy
        70-80   Fairly Easy
        60-70   Standard
        50-60   Fairly Difficult
        30-50   Difficult
        0-30    Very Confusing

    Args:
        text: Plain-text content to score.

    Returns:
        Flesch Reading Ease score (typically 0–100, may be negative for
        extremely complex text).
    """
    sentences = _tokenise_sentences(text)
    words = _tokenise_words(text)

    if not sentences or not words:
        return 0.0

    num_sentences = len(sentences)
    num_words = len(words)
    num_syllables = sum(_count_syllables(w) for w in words)

    asl = num_words / num_sentences          # average sentence length
    asw = num_syllables / num_words          # average syllables per word

    score = 206.835 - 1.015 * asl - 84.6 * asw
    return round(score, 2)


def flesch_kincaid_grade(text: str) -> float:
    """
    Compute the Flesch-Kincaid Grade Level for *text*.

    The result corresponds roughly to US school grade level required to
    understand the text (e.g., 8.0 ≈ 8th grade).

    Args:
        text: Plain-text content to score.

    Returns:
        FK Grade Level (float).
    """
    sentences = _tokenise_sentences(text)
    words = _tokenise_words(text)

    if not sentences or not words:
        return 0.0

    num_sentences = len(sentences)
    num_words = len(words)
    num_syllables = sum(_count_syllables(w) for w in words)

    asl = num_words / num_sentences
    asw = num_syllables / num_words

    grade = 0.39 * asl + 11.8 * asw - 15.59
    return round(grade, 2)


def _reading_ease_label(score: float) -> str:
    """Return a human-readable label for a Flesch Reading Ease score."""
    if score >= 90:
        return "Very Easy"
    if score >= 80:
        return "Easy"
    if score >= 70:
        return "Fairly Easy"
    if score >= 60:
        return "Standard"
    if score >= 50:
        return "Fairly Difficult"
    if score >= 30:
        return "Difficult"
    return "Very Confusing"


# ---------------------------------------------------------------------------
# Post-processor
# ---------------------------------------------------------------------------

class ReadabilityScorer(BasePostProcessor):
    """
    Post-processor that computes Flesch Reading Ease and Flesch-Kincaid Grade
    Level for the generated summary text.

    Results are stored in ``summary.metadata["readability"]`` as a dict:

    .. code-block:: python

        {
            "flesch_reading_ease": 65.3,
            "flesch_reading_ease_label": "Standard",
            "flesch_kincaid_grade": 9.1,
        }
    """

    name = "readability_scorer"
    description = (
        "Computes Flesch Reading Ease and Flesch-Kincaid Grade Level for the "
        "generated summary and stores results in summary.metadata['readability']."
    )

    def process(self, summary: Summary, article_text: str, **kwargs: Any) -> Summary:
        """
        Score the summary text and attach readability metadata.

        Args:
            summary: The Summary produced by the LLM.
            article_text: The original article text (unused by this processor).
            **kwargs: Not used; accepted for API compatibility.

        Returns:
            The same Summary with ``metadata["readability"]`` populated.
        """
        # Prefer a dedicated text field; fall back gracefully
        summary_text: str = ""
        if hasattr(summary, "summary") and isinstance(summary.summary, str):
            summary_text = summary.summary
        elif hasattr(summary, "text") and isinstance(summary.text, str):
            summary_text = summary.text
        else:
            summary_text = str(summary)

        if not summary_text.strip():
            return summary

        ease = flesch_reading_ease(summary_text)
        grade = flesch_kincaid_grade(summary_text)

        if not hasattr(summary, "metadata") or summary.metadata is None:
            summary.metadata = {}

        summary.metadata["readability"] = {
            "flesch_reading_ease": ease,
            "flesch_reading_ease_label": _reading_ease_label(ease),
            "flesch_kincaid_grade": grade,
        }
        return summary