"""
Built-in post-processor: KeywordExtractor

Extracts the top-N keywords from the original article text using a simple
TF-IDF implementation that has no external dependencies.  If NLTK is installed
and the 'stopwords' corpus is available the stop-word list is used; otherwise
a built-in English stop-word list is used as fallback.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, List, Optional

from summarizer.plugins.base import BasePostProcessor

# ---------------------------------------------------------------------------
# Minimal built-in English stop-words (used when NLTK is not available)
# ---------------------------------------------------------------------------
_BUILTIN_STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are aren't as at be
    because been before being below between both but by can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further get got had hadn't has hasn't have haven't having he he'd
    he'll he's her here here's hers herself him himself his how how's i i'd
    i'll i'm i've if in into is isn't it it's its itself let's me more most
    mustn't my myself no nor not of off on once only or other ought our ours
    ourselves out over own same shan't she she'd she'll she's should
    shouldn't so some such than that that's the their theirs them themselves
    then there there's these they they'd they'll they're they've this those
    through to too under until up very was wasn't we we'd we'll we're we've
    were weren't what what's when when's where where's which while who who's
    whom why why's will with won't would wouldn't you you'd you'll you're
    you've your yours yourself yourselves
    """.split()
)


def _get_stopwords() -> frozenset:
    try:
        from nltk.corpus import stopwords  # type: ignore

        return frozenset(stopwords.words("english"))
    except Exception:
        return _BUILTIN_STOPWORDS


def _tokenize(text: str) -> List[str]:
    """Lowercase and split text into alphabetic tokens of length >= 2."""
    return [t for t in re.findall(r"[a-z]{2,}", text.lower())]


def _tf(tokens: List[str]) -> dict:
    counts = Counter(tokens)
    total = len(tokens) or 1
    return {w: c / total for w, c in counts.items()}


def _idf(term: str, documents: List[List[str]]) -> float:
    """Compute IDF for *term* across *documents* (list of token lists)."""
    containing = sum(1 for doc in documents if term in doc)
    if containing == 0:
        return 0.0
    return math.log((1 + len(documents)) / (1 + containing)) + 1


def extract_keywords(text: str, top_n: int = 10, extra_stopwords: Optional[frozenset] = None) -> List[str]:
    """
    Return the top *top_n* keywords from *text* using TF-IDF over sentences.

    Args:
        text: The source text.
        top_n: Number of keywords to return.
        extra_stopwords: Additional words to ignore.

    Returns:
        List of keyword strings, highest scoring first.
    """
    stopwords = _get_stopwords()
    if extra_stopwords:
        stopwords = stopwords | extra_stopwords

    # Split into sentence-level "documents" for IDF
    sentences = re.split(r"[.!?]+", text)
    docs: List[List[str]] = [
        [t for t in _tokenize(s) if t not in stopwords] for s in sentences if s.strip()
    ]
    if not docs:
        return []

    all_tokens = [t for doc in docs for t in doc]
    if not all_tokens:
        return []

    tf_scores = _tf(all_tokens)
    tfidf = {term: tf * _idf(term, docs) for term, tf in tf_scores.items()}

    ranked = sorted(tfidf.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in ranked[:top_n]]


class KeywordExtractor(BasePostProcessor):
    """
    Post-processor that extracts the top-N keywords from the article text
    and attaches them to ``summary.keywords`` (created if absent).

    Configuration can be passed at instantiation::

        KeywordExtractor(top_n=15)
    """

    name: str = "keyword_extractor"
    description: str = (
        "Extracts the top-N keywords from the original article using TF-IDF. "
        "Attaches results to summary.keywords."
    )

    def __init__(self, top_n: int = 10) -> None:
        self.top_n = top_n

    def process(self, summary: Any, article_text: Optional[str] = None) -> Any:
        """
        Attach a 'keywords' attribute to *summary*.

        Args:
            summary: The Summary object to augment.
            article_text: The original article body; if None the summary's
                          own text fields are used as a fallback.

        Returns:
            The augmented summary object.
        """
        source_text = article_text or ""
        if not source_text:
            # Fallback: use whatever text fields are on the summary
            parts = []
            for attr in ("text", "content", "summary", "body"):
                val = getattr(summary, attr, None)
                if isinstance(val, str) and val:
                    parts.append(val)
            source_text = " ".join(parts)

        keywords = extract_keywords(source_text, top_n=self.top_n)
        try:
            summary.keywords = keywords
        except AttributeError:
            # Frozen dataclass or similar — wrap in a plain object
            object.__setattr__(summary, "keywords", keywords)

        return summary