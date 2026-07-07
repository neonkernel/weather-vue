"""Built-in post-processor: computes Flesch-Kincaid readability score for the summary."""

from __future__ import annotations

import re
from typing import List

from summarizer.plugins.base import BasePostProcessor

# ---------------------------------------------------------------------------
# Syllable counting heuristics
# ---------------------------------------------------------------------------
_VOWELS = re.compile(r"[aeiouy]+", re.IGNORECASE)
_SILENT_E = re.compile(r"[^aeiou]e$", re.IGNORECASE)
_DIPHTONG = re.compile(r"[aeiou]{2}", re.IGNORECASE)


def _count_syllables(word: str) -> int:
    """Estimate the number of syllables in an English word."""
    word = word.lower().strip(". ,;:!?\"'")
    if not word:
        return 0
    count = len(_VOWELS.findall(word))
    # Subtract silent trailing 'e'
    if len(word) > 2 and _SILENT_E.search(word):
        count -= 1
    return max(1, count)


def _sentences(text: str) -> List[str]:
    """Split text into sentences on '.', '!', '?'."""
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


def _words(text: str) -> List[str]:
    """Split text into words."""
    return [w for w in re.split(r"\s+", text) if w]


def flesch_reading_ease(text: str) -> float:
    """Compute the Flesch Reading Ease score for *text*.

    Higher scores (~70–100) indicate easy-to-read text;
    lower scores (<30) indicate very difficult text.

    Returns
    -------
    float in the range [0, 100] (clamped).
    """
    sents = _sentences(text)
    words = _words(text)
    n_sentences = max(len(sents), 1)
    n_words = max(len(words), 1)
    n_syllables = sum(_count_syllables(w) for w in words)

    asl = n_words / n_sentences  # average sentence length
    asw = n_syllables / n_words  # average syllables per word
    score = 206.835 - (1.015 * asl) - (84.6 * asw)
    return round(max(0.0, min(100.0, score)), 2)


def flesch_kincaid_grade(text: str) -> float:
    """Compute the Flesch-Kincaid Grade Level for *text*.

    Returns
    -------
    float representing the US school grade level needed to comprehend the text.
    """
    sents = _sentences(text)
    words = _words(text)
    n_sentences = max(len(sents), 1)
    n_words = max(len(words), 1)
    n_syllables = sum(_count_syllables(w) for w in words)

    asl = n_words / n_sentences
    asw = n_syllables / n_words
    grade = (0.39 * asl) + (11.8 * asw) - 15.59
    return round(max(0.0, grade), 2)


def readability_label(score: float) -> str:
    """Map a Flesch Reading Ease *score* to a human-readable label."""
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
    """Computes Flesch Reading Ease and Flesch-Kincaid Grade Level for the summary text.

    Results are stored in ``summary.metadata["readability"]`` as a dict:

    .. code-block:: python

        {
            "flesch_reading_ease": 72.3,
            "flesch_kincaid_grade": 8.1,
            "label": "Fairly Easy",
        }
    """

    name = "readability_scorer"
    description = (
        "Computes Flesch Reading Ease and Flesch-Kincaid Grade Level "
        "for the summary text; stores results in summary.metadata['readability']."
    )

    def process(self, summary, article_text: str):  # type: ignore[override]
        """Annotate *summary* with readability scores and return it."""
        summary_text = getattr(summary, "summary", "") or ""
        if not summary_text:
            return summary

        fre = flesch_reading_ease(summary_text)
        fkg = flesch_kincaid_grade(summary_text)

        readability = {
            "flesch_reading_ease": fre,
            "flesch_kincaid_grade": fkg,
            "label": readability_label(fre),
        }

        if not hasattr(summary, "metadata") or summary.metadata is None:
            try:
                summary.metadata = {}
            except AttributeError:
                return summary

        try:
            summary.metadata["readability"] = readability
        except (AttributeError, TypeError):
            pass

        return summary