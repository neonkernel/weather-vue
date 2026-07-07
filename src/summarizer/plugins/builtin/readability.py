"""
Built-in post-processor: computes a Flesch-Kincaid readability score for the
summary text and attaches it to the summary object.

No external dependencies are required — the Flesch Reading Ease formula is
implemented here directly.

Flesch Reading Ease
-------------------
    score = 206.835
            - 1.015  * (words / sentences)
            - 84.6   * (syllables / words)

Interpretation (approximate):
    90–100  Very Easy
    80–90   Easy
    70–80   Fairly Easy
    60–70   Standard
    50–60   Fairly Difficult
    30–50   Difficult
    0–30    Very Confusing
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from ..base import BasePostProcessor


# ---------------------------------------------------------------------------
# Syllable counting heuristic (no CMU dict / NLTK required)
# ---------------------------------------------------------------------------

_VOWELS = re.compile(r"[aeiouy]+", re.IGNORECASE)
_SILENT_E = re.compile(r"[^aeiou]e$", re.IGNORECASE)
_DOUBLE_VOWELS = re.compile(r"[aeiou]{2}", re.IGNORECASE)


def _count_syllables(word: str) -> int:
    word = word.lower().strip(". ,;:\"'")
    if not word:
        return 0
    count = len(_VOWELS.findall(word))
    if word.endswith("e") and len(word) > 2 and not re.search(r"[aeiou]e$", word[:-1]):
        count -= 1
    return max(1, count)


def _syllables_in_text(text: str) -> int:
    return sum(_count_syllables(w) for w in text.split())


def _sentence_count(text: str) -> int:
    sentences = re.split(r"[.!?]+", text)
    return max(1, sum(1 for s in sentences if s.strip()))


def flesch_reading_ease(text: str) -> float:
    """Return the Flesch Reading Ease score for *text* (0–100 scale)."""
    words = text.split()
    word_count = len(words)
    if word_count < 2:
        return 0.0

    sentence_count = _sentence_count(text)
    syllable_count = _syllables_in_text(text)

    score = (
        206.835
        - 1.015 * (word_count / sentence_count)
        - 84.6 * (syllable_count / word_count)
    )
    # Clamp to [0, 100]
    return round(max(0.0, min(100.0, score)), 2)


def _grade_label(score: float) -> str:
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


class ReadabilityScorer(BasePostProcessor):
    """
    Computes the Flesch Reading Ease score for the summary text and attaches
    ``summary.readability_score`` and ``summary.readability_label`` to the
    summary object.
    """

    name = "readability_scorer"
    description = (
        "Computes Flesch Reading Ease score for the summary text and attaches "
        "`summary.readability_score` and `summary.readability_label`."
    )

    def process(
        self,
        summary: Any,
        *,
        article_text: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        # Prefer the summary text over the raw article for readability
        text = getattr(summary, "summary", None) or getattr(summary, "content", None) or ""
        if not text and isinstance(summary, str):
            text = summary

        score = flesch_reading_ease(text) if text.strip() else 0.0
        label = _grade_label(score)

        for attr, val in [("readability_score", score), ("readability_label", label)]:
            try:
                object.__setattr__(summary, attr, val)
            except (AttributeError, TypeError):
                try:
                    setattr(summary, attr, val)
                except AttributeError:
                    pass

        return summary