"""
Built-in post-processor: KeywordExtractor

Extracts the top-N keywords from the original article text using a simple
TF-IDF-style approach. No external NLP library is required — the implementation
uses only the Python standard library so that it works in all environments.

If NLTK is available and its stopwords corpus is present, it will be used for a
richer stopword list; otherwise the built-in English stopword set is used.

The extracted keywords are stored in ``summary.metadata["keywords"]`` as a list
of ``{"term": str, "score": float}`` dicts, sorted by descending score.
"""

from __future__ import annotations

import logging
import math
import re
import string
from collections import Counter
from typing import Dict, List

from summarizer.models import Summary
from summarizer.plugins.base import BasePostProcessor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in English stopwords (sufficient fallback when NLTK is absent)
# ---------------------------------------------------------------------------

_BUILTIN_STOPWORDS: frozenset = frozenset(
    {
        "a", "about", "above", "after", "again", "against", "all", "am", "an",
        "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
        "before", "being", "below", "between", "both", "but", "by", "can't",
        "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
        "doing", "don't", "down", "during", "each", "few", "for", "from",
        "further", "get", "got", "had", "hadn't", "has", "hasn't", "have",
        "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
        "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
        "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
        "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
        "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
        "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
        "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
        "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
        "their", "theirs", "them", "themselves", "then", "there", "there's",
        "these", "they", "they'd", "they'll", "they're", "they've", "this",
        "those", "through", "to", "too", "under", "until", "up", "very", "was",
        "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
        "what", "what's", "when", "when's", "where", "where's", "which",
        "while", "who", "who's", "whom", "why", "why's", "will", "with",
        "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
        "you've", "your", "yours", "yourself", "yourselves",
    }
)


def _get_stopwords() -> frozenset:
    """Return a stopword set, preferring NLTK if available."""
    try:
        from nltk.corpus import stopwords as nltk_sw
        words = frozenset(nltk_sw.words("english"))
        logger.debug("KeywordExtractor: using NLTK stopwords (%d words).", len(words))
        return words
    except Exception:
        logger.debug("KeywordExtractor: NLTK unavailable; using built-in stopwords.")
        return _BUILTIN_STOPWORDS


def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, and split text into word tokens."""
    text = text.lower()
    # Replace hyphens/dashes with spaces so "state-of-the-art" → three tokens
    text = re.sub(r"[-–—]", " ", text)
    # Remove all remaining punctuation
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text.split()


def _compute_tfidf(
    doc_tokens: List[str],
    stopwords: frozenset,
    top_n: int,
) -> List[Dict]:
    """
    Compute a lightweight single-document TF-IDF score for each term.

    Since we have only one document, IDF is approximated using term frequency
    within the document itself (terms that appear in many sentences are penalised).

    Returns a list of {"term": str, "score": float} sorted by descending score.
    """
    if not doc_tokens:
        return []

    # Filter stopwords and short tokens
    filtered = [t for t in doc_tokens if t not in stopwords and len(t) > 2]
    if not filtered:
        return []

    total = len(filtered)
    tf: Counter = Counter(filtered)

    # Approximate IDF: penalise very common terms using log compression
    scores = {}
    for term, count in tf.items():
        term_freq = count / total
        # Smooth IDF: log(total / count) — higher score for rarer terms
        idf = math.log((total + 1) / (count + 1)) + 1.0
        scores[term] = term_freq * idf

    sorted_terms = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"term": t, "score": round(s, 6)} for t, s in sorted_terms[:top_n]]


class KeywordExtractor(BasePostProcessor):
    """
    Post-processor that extracts top-N keywords from the article text.

    Keywords are stored in ``summary.metadata["keywords"]`` as a list of
    ``{"term": str, "score": float}`` dicts sorted by descending TF-IDF score.

    Configuration:
        top_n (int): Number of keywords to extract. Default: 10.
    """

    name = "keyword_extractor"
    description = (
        "Extracts the top-N keywords from the article using TF-IDF scoring "
        "and stores them in summary.metadata['keywords']."
    )

    def __init__(self, top_n: int = 10) -> None:
        self.top_n = top_n
        self._stopwords = _get_stopwords()

    def process(self, summary: Summary, article_text: str = "") -> Summary:
        """
        Extract keywords from article_text and attach them to the summary.

        If article_text is empty, falls back to the summary text itself.

        Args:
            summary: The Summary object to enrich.
            article_text: The original article plain text.

        Returns:
            The same Summary object with ``metadata["keywords"]`` populated.
        """
        source = article_text.strip() or (summary.summary if hasattr(summary, "summary") else "")

        if not source:
            logger.debug("KeywordExtractor: no source text available; skipping.")
            return summary

        tokens = _tokenize(source)
        keywords = _compute_tfidf(tokens, self._stopwords, self.top_n)

        # Ensure metadata dict exists
        if not hasattr(summary, "metadata") or summary.metadata is None:
            try:
                summary.metadata = {}
            except AttributeError:
                logger.warning(
                    "KeywordExtractor: Summary.metadata is not settable; "
                    "keyword results will be discarded."
                )
                return summary

        summary.metadata["keywords"] = keywords
        logger.debug(
            "KeywordExtractor: extracted %d keywords: %s",
            len(keywords),
            [k["term"] for k in keywords],
        )
        return summary