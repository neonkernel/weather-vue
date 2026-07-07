"""
Built-in post-processor: ReadabilityScorer

Computes the Flesch-Kincaid readability score for the summary text and attaches
the result to ``summary.metadata["readability"]``.

The Flesch Reading Ease formula is:
    206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)

The Flesch-Kincaid Grade Level formula is:
    0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

Both scores are computed using only the Python standard library — no external
NLP packages are required.

Score interpretation (Flesch Reading Ease):
  90–100  Very easy  (5th grade)
  80–90   Easy
  70–80   Fairly easy
  60–70   Standard
  50–60   Fairly difficult
  30–50   Difficult
  0–30    Very confusing
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Tuple

from summarizer.models import Summary
from summarizer.plugins.base import BasePostProcessor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Syllable counting (heuristic, English only)
# ---------------------------------------------------------------------------

# Vowel groups (each group counts as one syllable)
_VOWELS = re.compile(r"[aeiouy]+", re.IGNORECASE)

# Silent 'e' at end of word
_SILENT_E = re.compile(r"e$", re.IGNORECASE)

# Common suffixes that typically don't add a syllable
_SUFFIXES_NO_SYLLABLE = re.compile(r"(ed|es|ing)$", re.IGNORECASE)


def _count_syllables_word(word: str) -> int:
    """
    Count syllables in a single word using heuristics.

    Returns at least 1 for any non-empty word.
    """
    word = word.lower().strip()
    if not word:
        return 0

    # Strip trailing punctuation
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0

    count = len(_VOWELS.findall(word))

    # Deduct for silent 'e' at end (e.g. "cake" → 1 vowel group, no deduction needed
    # but "the" → 1 without deduction which is correct)
    if len(word) > 2 and _SILENT_E.search(word):
        count -= 1

    # Deduct for common suffixes that don't add syllables in many cases
    # (simple heuristic — not perfect but acceptable for scoring)
    # e.g. "walked" → 1 syllable, "running" → 2 syllables
    # We only deduct if the base word already has vowels
    # (Skipping this heuristic as it reduces accuracy — using simple vowel count instead)

    return max(1, count)


def _count_syllables(text: str) -> int:
    """Count total syllables in a block of text."""
    words = re.findall(r"[a-zA-Z]+", text)
    return sum(_count_syllables_word(w) for w in words)


def _count_sentences(text: str) -> int:
    """
    Count the number of sentences in text.

    Uses a simple heuristic: split on sentence-ending punctuation.
    Returns at least 1.
    """
    # Split on '.', '!', '?' optionally followed by quotes/spaces
    sentences = re.split(r"[.!?]+[\s\"']*", text.strip())
    # Filter empty strings
    count = sum(1 for s in sentences if s.strip())
    return max(1, count)


def _count_words(text: str) -> int:
    """Count the number of words in text. Returns at least 1."""
    words = re.findall(r"\b[a-zA-Z']+\b", text)
    return max(1, len(words))


def _compute_flesch(text: str) -> Tuple[float, float]:
    """
    Compute Flesch Reading Ease and Flesch-Kincaid Grade Level for text.

    Returns:
        (flesch_ease, flesch_kincaid_grade) as a tuple of floats.
    """
    sentences = _count_sentences(text)
    words = _count_words(text)
    syllables = _count_syllables(text)

    asl = words / sentences  # Average sentence length
    asw = syllables / words  # Average syllables per word

    ease = 206.835 - (1.015 * asl) - (84.6 * asw)
    grade = (0.39 * asl) + (11.8 * asw) - 15.59

    # Clamp ease to [0, 100]
    ease = max(0.0, min(100.0, ease))

    return round(ease, 2), round(grade, 2)


def _grade_label(ease: float) -> str:
    """Return a human-readable difficulty label for the Flesch ease score."""
    if ease >= 90:
        return "Very Easy"
    elif ease >= 80:
        return "Easy"
    elif ease >= 70:
        return "Fairly Easy"
    elif ease >= 60:
        return "Standard"
    elif ease >= 50:
        return "Fairly Difficult"
    elif ease >= 30:
        return "Difficult"
    else:
        return "Very Confusing"


class ReadabilityScorer(BasePostProcessor):
    """
    Post-processor that computes Flesch-Kincaid readability scores for the
    summary text.

    Results are stored in ``summary.metadata["readability"]`` as::

        {
            "flesch_ease": float,          # 0–100; higher is easier
            "flesch_kincaid_grade": float, # US school grade level
            "label": str,                  # human-readable difficulty
            "word_count": int,
            "sentence_count": int,
            "syllable_count": int,
        }
    """

    name = "readability_scorer"
    description = (
        "Computes Flesch Reading Ease and Flesch-Kincaid Grade Level for the "
        "summary text and stores the scores in summary.metadata['readability']."
    )

    def process(self, summary: Summary, article_text: str = "") -> Summary:
        """
        Compute readability scores and attach them to the summary.

        Scores are always computed against the summary text itself (not the
        original article), because that reflects the quality of the generated
        summary.

        Args:
            summary: The Summary object to enrich.
            article_text: Unused by this post-processor (kept for API compatibility).

        Returns:
            The same Summary object with ``metadata["readability"]`` populated.
        """
        summary_text = getattr(summary, "summary", "") or ""
        if not summary_text.strip():
            logger.debug("ReadabilityScorer: empty summary text; skipping.")
            return summary

        ease, grade = _compute_flesch(summary_text)

        readability: Dict = {
            "flesch_ease": ease,
            "flesch_kincaid_grade": round(grade, 2),
            "label": _grade_label(ease),
            "word_count": _count_words(summary_text),
            "sentence_count": _count_sentences(summary_text),
            "syllable_count": _count_syllables(summary_text),
        }

        # Ensure metadata dict exists
        if not hasattr(summary, "metadata") or summary.metadata is None:
            try:
                summary.metadata = {}
            except AttributeError:
                logger.warning(
                    "ReadabilityScorer: Summary.metadata is not settable; "
                    "readability results will be discarded."
                )
                return summary

        summary.metadata["readability"] = readability
        logger.debug(
            "ReadabilityScorer: ease=%.2f, grade=%.2f, label=%s",
            ease,
            grade,
            readability["label"],
        )
        return summary