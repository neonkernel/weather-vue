"""
Built-in post-processor: ReadabilityScorer
==========================================

Computes a Flesch-Kincaid readability score for the *summary text* and stores
it in ``summary.metadata``.

The Flesch Reading Ease formula requires only syllable counts, word counts,
and sentence counts – no external libraries are needed.  An optional
Flesch-Kincaid Grade Level score is also computed.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from ...models import Summary
from ..base import BasePostProcessor


class ReadabilityScorer(BasePostProcessor):
    """
    Post-processor that adds Flesch-Kincaid readability metrics to a summary.

    The following keys are added to ``summary.metadata``:

    * ``readability_ease`` – Flesch Reading Ease score (0–100).
      Higher values indicate easier text.
    * ``readability_grade`` – Flesch-Kincaid Grade Level.
      Approximates the US school grade needed to comprehend the text.
    * ``readability_label`` – A human-friendly label such as "Easy" or
      "Very Difficult".

    Reference:
        Flesch, R. (1948). A new readability yardstick. *Journal of Applied
        Psychology*, 32(3), 221–233.
    """

    name = "readability_scorer"
    description = "Computes Flesch-Kincaid readability scores for the summary text"
    version = "1.0.0"

    def process(self, summary: Summary, original_text: str, **kwargs: Any) -> Summary:
        """
        Compute readability scores from the summary text.

        Args:
            summary: The Summary produced by the LLM.
            original_text: The raw article text (not used by this processor).
            **kwargs: Unused.

        Returns:
            The same *summary* with readability metadata populated.
        """
        text: str = summary.text or ""

        if not text.strip():
            scores: Dict[str, object] = {
                "readability_ease": None,
                "readability_grade": None,
                "readability_label": "N/A",
            }
        else:
            ease, grade = _flesch_kincaid(text)
            scores = {
                "readability_ease": round(ease, 2),
                "readability_grade": round(grade, 2),
                "readability_label": _ease_label(ease),
            }

        if summary.metadata is None:
            summary.metadata = {}
        summary.metadata.update(scores)
        return summary


# ---------------------------------------------------------------------------
# Flesch-Kincaid implementation (no external dependencies)
# ---------------------------------------------------------------------------


def _count_sentences(text: str) -> int:
    """Count sentences by splitting on terminal punctuation."""
    sentences = re.split(r"[.!?]+", text)
    # Filter out empty strings that result from trailing punctuation
    return max(1, sum(1 for s in sentences if s.strip()))


def _count_words(text: str) -> int:
    """Count whitespace-delimited tokens."""
    return max(1, len(text.split()))


def _count_syllables_in_word(word: str) -> int:
    """
    Estimate syllable count using a heuristic approach.

    This is not perfect but is acceptable for readability scoring purposes
    and requires no external dictionary.
    """
    word = word.lower().strip(".,!?;:'\"")
    if not word:
        return 0

    # Special cases
    if len(word) <= 3:
        return 1

    # Remove silent trailing 'e'
    word = re.sub(r"e$", "", word)

    # Count vowel groups as syllables
    vowel_groups = re.findall(r"[aeiouy]+", word)
    count = len(vowel_groups)

    # Adjust for common patterns
    # -le at the end counts as a syllable
    if word.endswith("le") and len(word) > 2 and word[-3] not in "aeiouy":
        count += 1

    return max(1, count)


def _count_syllables(text: str) -> int:
    """Count total syllables across all words in *text*."""
    words = text.split()
    return sum(_count_syllables_in_word(w) for w in words)


def _flesch_kincaid(text: str) -> Tuple[float, float]:
    """
    Compute Flesch Reading Ease and Flesch-Kincaid Grade Level.

    Returns:
        A tuple of ``(reading_ease, grade_level)``.
    """
    sentences = _count_sentences(text)
    words = _count_words(text)
    syllables = _count_syllables(text)

    # Flesch Reading Ease
    # RE = 206.835 – 1.015 * (words / sentences) – 84.6 * (syllables / words)
    reading_ease = (
        206.835
        - 1.015 * (words / sentences)
        - 84.6 * (syllables / words)
    )
    # Clamp to [0, 100]
    reading_ease = max(0.0, min(100.0, reading_ease))

    # Flesch-Kincaid Grade Level
    # GL = 0.39 * (words / sentences) + 11.8 * (syllables / words) – 15.59
    grade_level = (
        0.39 * (words / sentences)
        + 11.8 * (syllables / words)
        - 15.59
    )
    grade_level = max(0.0, grade_level)

    return reading_ease, grade_level


def _ease_label(score: float) -> str:
    """Convert a Flesch Reading Ease score to a descriptive label."""
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
        return "Very Difficult"