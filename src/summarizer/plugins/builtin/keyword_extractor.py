"""
Built-in post-processor: KeywordExtractor

Extracts the top N keywords from the original article text using a simple
TF-IDF-inspired approach (no external ML dependencies required).

If the `nltk` package is available it will be used for stop-word filtering;
otherwise a small built-in stop-word list is used as a fallback.
"""

from __future__ import annotations

import logging
import math
import re
import string
from collections import Counter
from typing import Any

from summarizer.plugins.base import BasePostProcessor

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Stop-word list (fallback when NLTK is not installed)
# -------------------------------------------------------------------------
_BUILTIN_STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "its", "was", "are", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "shall", "can",
        "not", "no", "nor", "so", "yet", "both", "either", "neither",
        "each", "few", "more", "most", "other", "some", "such", "than",
        "too", "very", "just", "that", "this", "these", "those", "which",
        "who", "whom", "what", "when", "where", "why", "how", "all", "any",
        "because", "as", "until", "while", "although", "though", "if",
        "then", "than", "into", "through", "during", "before", "after",
        "above", "below", "between", "out", "off", "over", "under", "again",
        "further", "once", "here", "there", "s", "t", "re", "ve", "ll",
        "d", "m", "their", "they", "them", "he", "she", "we", "you", "i",
        "me", "him", "her", "us", "my", "your", "his", "our", "its",
        "about", "up", "also", "said", "says", "like", "use", "used", "using",
    }
)


def _get_stopwords() -> frozenset[str]:
    """Return NLTK English stop-words if available, else the built-in set."""
    try:
        import nltk  # type: ignore

        try:
            from nltk.corpus import stopwords as sw

            return frozenset(sw.words("english"))
        except LookupError:
            nltk.download("stopwords", quiet=True)
            from nltk.corpus import stopwords as sw

            return frozenset(sw.words("english"))
    except ImportError:
        logger.debug("NLTK not available; using built-in stop-word list.")
        return _BUILTIN_STOPWORDS


def _tokenize(text: str) -> list[str]:
    """Lowercase, remove punctuation, split into tokens."""
    text = text.lower()
    text = re.sub(r"[" + re.escape(string.punctuation) + r"]", " ", text)
    return [tok for tok in text.split() if tok.isalpha() and len(tok) > 1]


def _tf_idf_keywords(
    tokens: list[str],
    stopwords: frozenset[str],
    top_n: int = 10,
) -> list[tuple[str, float]]:
    """
    Compute a simple single-document TF score (we treat each sentence as a
    "document" for the IDF component to penalise very common terms).

    Returns a sorted list of (keyword, score) pairs.
    """
    filtered = [t for t in tokens if t not in stopwords and len(t) > 2]
    if not filtered:
        return []

    total = len(filtered)
    tf: Counter = Counter(filtered)

    # For IDF we use a simple heuristic: penalise tokens that appear in
    # more than 20 % of the tokens (acts like a high-df penalty).
    scores: dict[str, float] = {}
    for word, count in tf.items():
        term_freq = count / total
        # Inverse weighting: rarer words score higher
        idf = math.log((total + 1) / (count + 1)) + 1.0
        scores[word] = term_freq * idf

    sorted_keywords = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_keywords[:top_n]


class KeywordExtractor(BasePostProcessor):
    """
    Extracts the top-N keywords from the article text and attaches them
    to the summary's metadata dict as ``keywords``.

    Configuration (passed via process() kwargs):
        top_n (int): Number of keywords to extract (default 10).
    """

    name = "keyword_extractor"
    description = (
        "Extracts top-N keywords from the article text using TF-IDF "
        "(NLTK-enhanced when available)."
    )
    enabled_by_default = True

    def __init__(self, top_n: int = 10) -> None:
        self.top_n = top_n
        self._stopwords: frozenset[str] | None = None

    @property
    def stopwords(self) -> frozenset[str]:
        if self._stopwords is None:
            self._stopwords = _get_stopwords()
        return self._stopwords

    def process(self, summary: Any, article_text: str = "", **kwargs: Any) -> Any:
        """
        Attach a 'keywords' list to summary.metadata.

        Args:
            summary: A Summary-like object with a .metadata dict attribute,
                     or any object (keywords are attached as an attribute).
            article_text: The original article text.
            **kwargs:
                top_n (int): Override the number of keywords to return.

        Returns:
            The enriched summary object.
        """
        top_n = int(kwargs.get("top_n", self.top_n))
        text = article_text or ""

        tokens = _tokenize(text)
        keyword_scores = _tf_idf_keywords(tokens, self.stopwords, top_n=top_n)
        keywords = [kw for kw, _ in keyword_scores]

        # Attach to summary.metadata if available, otherwise as attribute
        if hasattr(summary, "metadata") and isinstance(summary.metadata, dict):
            summary.metadata["keywords"] = keywords
        else:
            try:
                summary.keywords = keywords
            except AttributeError:
                logger.warning(
                    "Cannot attach keywords to summary of type %r",
                    type(summary).__name__,
                )

        logger.debug("KeywordExtractor extracted %d keywords.", len(keywords))
        return summary