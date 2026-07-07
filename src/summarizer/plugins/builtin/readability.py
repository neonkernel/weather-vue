"""
Built-in post-processor: ReadabilityScorer

Computes a Flesch-Kincaid readability score for the summary text and attaches
it as ``summary.readability``.  The implementation is self-contained and
requires no external dependencies.

Flesch Reading Ease formula:
    206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)

Flesch-Kincaid Grade Level formula:
    0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from summarizer.plugins.base import BasePostProcessor


# ---------------------------------------------------------------------------
# Syllable counting (approximation — avoids any external dependency)
# ---------------------------------------------------------------------------

_VOWELS = re.compile(r"[aeiouy]+", re.IGNORECASE)


def _count_syllables(word: str) -> int:
    """
    Approximate the number of syllables in an English word.

    Uses the heuristic:
      1. Count vowel groups.
      2. Subtract for silent-e endings.
      3. Ensure at least 1 syllable.
    """
    word = word.lower().rstrip(".,;:!?\"'")
    if not word:
        return 0
    count = len(_VOWELS.findall(word))
    # Silent 'e' at end
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _count_sentences(text: str) -> int:
    """Count sentences by splitting on terminal punctuation."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return max(1, len(sentences))


def _count_words(text: str) -> list:
    """Return list of word tokens."""
    return re.findall(r"\b[a-zA-Z']+\b", text)


@dataclass
class ReadabilityResult:
    """Container for readability metrics."""

    flesch_reading_ease: float
    flesch_kincaid_grade: float
    word_count: int
    sentence_count: int
    syllable_count: int
    avg_words_per_sentence: float
    avg_syllables_per_word: float
    interpretation: str

    def as_dict(self) -> dict:
        return {
            "flesch_reading_ease": self.flesch_reading_ease,
            "flesch_kincaid_grade": self.flesch_kincaid_grade,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "syllable_count": self.syllable_count,
            "avg_words_per_sentence": self.avg_words_per_sentence,
            "avg_syllables_per_word": self.avg_syllables_per_word,
            "interpretation": self.interpretation,
        }


def _interpret_reading_ease(score: float) -> str:
    """Map a Flesch Reading Ease score to a human-readable label."""
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


def compute_readability(text: str) -> ReadabilityResult:
    """
    Compute Flesch readability metrics for *text*.

    Args:
        text: The text to analyse.

    Returns:
        A :class:`ReadabilityResult` dataclass.
    """
    words = _count_words(text)
    num_words = len(words)
    num_sentences = _count_sentences(text)
    num_syllables = sum(_count_syllables(w) for w in words)

    avg_wps = num_words / num_sentences if num_sentences else 0.0
    avg_spw = num_syllables / num_words if num_words else 0.0

    # Flesch Reading Ease
    fre = 206.835 - 1.015 * avg_wps - 84.6 * avg_spw

    # Flesch-Kincaid Grade Level
    fkgl = 0.39 * avg_wps + 11.8 * avg_spw - 15.59

    return ReadabilityResult(
        flesch_reading_ease=round(fre, 2),
        flesch_kincaid_grade=round(fkgl, 2),
        word_count=num_words,
        sentence_count=num_sentences,
        syllable_count=num_syllables,
        avg_words_per_sentence=round(avg_wps, 2),
        avg_syllables_per_word=round(avg_spw, 2),
        interpretation=_interpret_reading_ease(fre),
    )


class ReadabilityScorer(BasePostProcessor):
    """
    Post-processor that computes Flesch-Kincaid readability metrics for the
    summary text and attaches them as ``summary.readability``.

    The scorer operates on the summary text fields in this priority order:
    ``summary``, ``text``, ``content``, ``body``.

    Example::

        scorer = ReadabilityScorer()
        summary = scorer.process(summary)
        print(summary.readability.flesch_reading_ease)
    """

    name: str = "readability_scorer"
    description: str = (
        "Computes Flesch-Kincaid readability metrics for the summary text. "
        "Attaches results to summary.readability."
    )

    def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
        """
        Compute readability and attach result to *summary*.

        Args:
            summary: The Summary object to augment.
            article_text: Ignored by this processor (operates on summary text).

        Returns:
            The augmented summary object.
        """
        source_text = ""
        for attr in ("summary", "text", "content", "body"):
            val = getattr(summary, attr, None)
            if isinstance(val, str) and val.strip():
                source_text = val
                break

        if source_text:
            result = compute_readability(source_text)
        else:
            # Return a zeroed result rather than fail
            result = ReadabilityResult(
                flesch_reading_ease=0.0,
                flesch_kincaid_grade=0.0,
                word_count=0,
                sentence_count=0,
                syllable_count=0,
                avg_words_per_sentence=0.0,
                avg_syllables_per_word=0.0,
                interpretation="N/A",
            )

        try:
            summary.readability = result
        except AttributeError:
            object.__setattr__(summary, "readability", result)

        return summary