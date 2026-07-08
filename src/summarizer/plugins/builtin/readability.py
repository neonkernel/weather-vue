"""
Built-in post-processor: ReadabilityScorer

Computes a Flesch-Kincaid readability score for the generated summary text
and attaches it to the summary's metadata dict.

The Flesch Reading Ease formula:
    206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)

The Flesch-Kincaid Grade Level formula:
    0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

No external dependencies are required — syllable counting uses a simple
heuristic that is accurate enough for informational prose.
"""

from __future__ import annotations

import logging
import re
import string
from typing import Any

from summarizer.plugins.base import BasePostProcessor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Syllable counting heuristic
# ---------------------------------------------------------------------------

_VOWELS = frozenset("aeiouy")

_EXCEPTIONS_ADD: list[str] = [
    "serious", "crucial", "area", "idea", "ocean", "visual",
    "actual", "usual", "trivial", "real", "ion",
]

_EXCEPTIONS_SUBTRACT: list[str] = [
    "every", "different", "family", "general", "natural",
    "business", "natural", "different",
]


def _count_syllables(word: str) -> int:
    """
    Estimate the number of syllables in a word using a rule-based heuristic.

    Accuracy: ~90 % on common English vocabulary.
    """
    word = word.lower().strip(string.punctuation)
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Remove trailing silent 'e'
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]

    # Count vowel groups
    count = 0
    prev_vowel = False
    for char in word:
        is_vowel = char in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    # 'le' at end of word counts as syllable if preceded by consonant
    if word.endswith("le") and len(word) > 2 and word[-3] not in _VOWELS:
        count += 1

    return max(1, count)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation heuristics."""
    # Split on '.', '!', '?' followed by whitespace or end of string
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s.strip()]


def _tokenize_words(text: str) -> list[str]:
    """Return list of alphabetic word tokens."""
    return [w for w in re.findall(r"[a-zA-Z']+", text) if w.isalpha()]


# ---------------------------------------------------------------------------
# Readability formulas
# ---------------------------------------------------------------------------

def flesch_reading_ease(
    word_count: int, sentence_count: int, syllable_count: int
) -> float:
    """
    Compute the Flesch Reading Ease score.

    Interpretation:
        90–100  Very Easy
        80–90   Easy
        70–80   Fairly Easy
        60–70   Standard
        50–60   Fairly Difficult
        30–50   Difficult
        0–30    Very Confusing
    """
    if sentence_count == 0 or word_count == 0:
        return 0.0
    return (
        206.835
        - 1.015 * (word_count / sentence_count)
        - 84.6 * (syllable_count / word_count)
    )


def flesch_kincaid_grade(
    word_count: int, sentence_count: int, syllable_count: int
) -> float:
    """
    Compute the Flesch-Kincaid Grade Level score.

    The result corresponds roughly to a US school grade level.
    """
    if sentence_count == 0 or word_count == 0:
        return 0.0
    return (
        0.39 * (word_count / sentence_count)
        + 11.8 * (syllable_count / word_count)
        - 15.59
    )


def _ease_label(score: float) -> str:
    """Return a human-readable label for a Flesch Reading Ease score."""
    if score >= 90:
        return "Very Easy"
    elif score >= 80:
        return "Easy"
    elif score >= 70:
        return "Fairly Easy"
    elif score >= 60:
        return "Standard"
    elif score >= 50:
        return "Fairly Difficult"
    elif score >= 30:
        return "Difficult"
    else:
        return "Very Confusing"


# ---------------------------------------------------------------------------
# Post-processor class
# ---------------------------------------------------------------------------

class ReadabilityScorer(BasePostProcessor):
    """
    Computes Flesch Reading Ease and Flesch-Kincaid Grade Level for
    the generated summary text and stores them in summary.metadata.

    Metadata keys added:
        readability_score       (float) Flesch Reading Ease score (0–100)
        readability_label       (str)   Human-readable ease label
        flesch_kincaid_grade    (float) FK Grade Level
        readability_word_count  (int)   Word count of the summary
        readability_sentence_count (int) Sentence count of the summary
    """

    name = "readability_scorer"
    description = (
        "Computes Flesch-Kincaid readability scores for the generated summary "
        "(no external dependencies)."
    )
    enabled_by_default = True

    def process(self, summary: Any, article_text: str = "", **kwargs: Any) -> Any:
        """
        Compute readability metrics for the summary text.

        Args:
            summary: A Summary-like object. The summary text is read from
                     summary.text, summary.content, or str(summary).
            article_text: Unused by this processor (but accepted for API compat).
            **kwargs: Ignored.

        Returns:
            The enriched summary object.
        """
        text = self._get_text(summary)
        if not text.strip():
            logger.debug("ReadabilityScorer: empty summary text — skipping.")
            return summary

        sentences = _split_sentences(text)
        words = _tokenize_words(text)
        syllables = sum(_count_syllables(w) for w in words)

        sentence_count = max(1, len(sentences))
        word_count = max(1, len(words))

        ease = flesch_reading_ease(word_count, sentence_count, syllables)
        grade = flesch_kincaid_grade(word_count, sentence_count, syllables)
        label = _ease_label(ease)

        metrics = {
            "readability_score": round(ease, 2),
            "readability_label": label,
            "flesch_kincaid_grade": round(grade, 2),
            "readability_word_count": word_count,
            "readability_sentence_count": sentence_count,
        }

        if hasattr(summary, "metadata") and isinstance(summary.metadata, dict):
            summary.metadata.update(metrics)
        else:
            for key, value in metrics.items():
                try:
                    setattr(summary, key, value)
                except AttributeError:
                    logger.warning(
                        "Cannot set readability attribute %r on %r",
                        key,
                        type(summary).__name__,
                    )

        logger.debug(
            "ReadabilityScorer: ease=%.1f (%s), grade=%.1f, words=%d, sentences=%d",
            ease,
            label,
            grade,
            word_count,
            sentence_count,
        )
        return summary

    @staticmethod
    def _get_text(summary: Any) -> str:
        """Extract plain text from a Summary-like object."""
        for attr in ("text", "content", "summary", "body"):
            val = getattr(summary, attr, None)
            if isinstance(val, str) and val.strip():
                return val
        return str(summary)