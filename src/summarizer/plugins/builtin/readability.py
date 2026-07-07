"""Built-in post-processor: computes a Flesch-Kincaid readability score.

The Flesch Reading Ease formula is::

    206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)

Higher scores indicate easier text (max ≈ 121).  The Flesch-Kincaid Grade
Level is also computed::

    0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

Both values are stored in ``summary.metadata``.

No external dependencies are required; syllable counting uses a simple
vowel-group heuristic.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Tuple


from ..base import BasePostProcessor


# ---------------------------------------------------------------------------
# Readability helpers
# ---------------------------------------------------------------------------


def _count_syllables(word: str) -> int:
    """Estimate syllables in *word* using a vowel-group heuristic."""
    word = word.lower().strip(".,!?;:\"'")
    if not word:
        return 0
    # Count vowel groups
    vowels = re.findall(r"[aeiouy]+", word)
    count = len(vowels)
    # Adjust for silent trailing 'e'
    if word.endswith("e") and len(word) > 2:
        count = max(1, count - 1)
    return max(1, count)


def _count_sentences(text: str) -> int:
    """Count sentences by splitting on terminal punctuation."""
    sentences = re.split(r"[.!?]+", text.strip())
    return max(1, sum(1 for s in sentences if s.strip()))


def _analyse_text(text: str) -> Tuple[int, int, int]:
    """Return (word_count, sentence_count, syllable_count)."""
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)
    sentence_count = _count_sentences(text)
    syllable_count = sum(_count_syllables(w) for w in words)
    return word_count, sentence_count, syllable_count


def flesch_reading_ease(words: int, sentences: int, syllables: int) -> float:
    """Return the Flesch Reading Ease score (0–100 scale, higher = easier)."""
    if words == 0 or sentences == 0:
        return 0.0
    return 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)


def flesch_kincaid_grade(words: int, sentences: int, syllables: int) -> float:
    """Return the Flesch-Kincaid Grade Level."""
    if words == 0 or sentences == 0:
        return 0.0
    return 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59


def reading_ease_label(score: float) -> str:
    """Map a Flesch Reading Ease score to a human-readable difficulty label."""
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
# Plugin class
# ---------------------------------------------------------------------------


class ReadabilityScorer(BasePostProcessor):
    """Computes Flesch readability metrics for the *summary text* and stores
    them under ``summary.metadata["readability"]``.

    The metadata entry is a dict with keys:

    ``flesch_reading_ease``
        Float 0–100; higher is easier.
    ``flesch_kincaid_grade``
        Approximate US school grade level required to understand the text.
    ``reading_ease_label``
        Human-readable difficulty label (e.g. "Standard").
    ``word_count``
        Number of words in the summary.
    ``sentence_count``
        Number of sentences in the summary.
    ``syllable_count``
        Estimated total syllables.
    """

    name = "readability"
    description = "Computes Flesch-Kincaid readability scores for the summary text."
    version = "1.0.0"

    def process(self, summary: Any, article_text: str = "") -> Any:
        """Attach readability metrics to ``summary.metadata["readability"]``."""
        text: str = getattr(summary, "text", "") or ""
        if not text.strip():
            return summary

        words, sentences, syllables = _analyse_text(text)
        ease = flesch_reading_ease(words, sentences, syllables)
        grade = flesch_kincaid_grade(words, sentences, syllables)

        readability: Dict[str, Any] = {
            "flesch_reading_ease": round(ease, 2),
            "flesch_kincaid_grade": round(grade, 2),
            "reading_ease_label": reading_ease_label(ease),
            "word_count": words,
            "sentence_count": sentences,
            "syllable_count": syllables,
        }

        try:
            # Pydantic v2 model_copy
            existing_meta: Dict[str, Any] = dict(getattr(summary, "metadata", {}) or {})
            existing_meta["readability"] = readability
            summary = summary.model_copy(update={"metadata": existing_meta})
        except AttributeError:
            try:
                if not hasattr(summary, "metadata") or summary.metadata is None:
                    summary.metadata = {}
                summary.metadata["readability"] = readability
            except (AttributeError, TypeError):
                pass

        return summary