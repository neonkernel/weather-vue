"""
Built-in post-processor: KeywordExtractor
=========================================

Extracts the top-N keywords from the *original article text* using a simple
TF-IDF approach that requires no external dependencies beyond the Python
standard library.

If ``scikit-learn`` is installed the implementation will use its
``TfidfVectorizer`` for higher quality results; otherwise it falls back to a
pure-Python TF-IDF computation.
"""

from __future__ import annotations

import math
import re
import string
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from ...models import Summary
from ..base import BasePostProcessor

# ---------------------------------------------------------------------------
# Optional scikit-learn import
# ---------------------------------------------------------------------------

try:
    from sklearn.feature_extraction.text import TfidfVectorizer as _SklearnTfidf  # type: ignore

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Common English stop-words (minimal set – no external dependency)
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset = frozenset(
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


class KeywordExtractor(BasePostProcessor):
    """
    Post-processor that extracts the top-N keywords from the original article.

    Keywords are stored in ``summary.metadata["keywords"]`` as a list of
    strings.  The number of keywords is controlled by ``top_n`` (default 10).

    Example metadata output::

        {"keywords": ["machine learning", "neural network", "training data"]}
    """

    name = "keyword_extractor"
    description = "Extracts top-N keywords from the original article using TF-IDF"
    version = "1.0.0"

    def __init__(self, top_n: int = 10) -> None:
        self.top_n = top_n

    def process(self, summary: Summary, original_text: str, **kwargs: Any) -> Summary:
        """
        Enrich *summary* with a ``keywords`` list in its metadata.

        Args:
            summary: The Summary produced by the LLM.
            original_text: The raw article text.
            **kwargs: ``top_n`` overrides the instance default if provided.

        Returns:
            The same *summary* object with ``metadata["keywords"]`` populated.
        """
        top_n: int = kwargs.get("top_n", self.top_n)

        if not original_text or not original_text.strip():
            keywords: List[str] = []
        elif _SKLEARN_AVAILABLE:
            keywords = self._sklearn_keywords(original_text, top_n)
        else:
            keywords = self._builtin_keywords(original_text, top_n)

        if summary.metadata is None:
            summary.metadata = {}
        summary.metadata["keywords"] = keywords
        return summary

    # ------------------------------------------------------------------
    # scikit-learn implementation
    # ------------------------------------------------------------------

    def _sklearn_keywords(self, text: str, top_n: int) -> List[str]:
        vectorizer = _SklearnTfidf(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=200,
        )
        try:
            tfidf_matrix = vectorizer.fit_transform([text])
        except ValueError:
            return []

        feature_names: List[str] = vectorizer.get_feature_names_out().tolist()
        scores = tfidf_matrix.toarray()[0]
        ranked = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
        return [term for term, _ in ranked[:top_n]]

    # ------------------------------------------------------------------
    # Pure-Python TF-IDF fallback
    # ------------------------------------------------------------------

    def _builtin_keywords(self, text: str, top_n: int) -> List[str]:
        tokens = self._tokenise(text)
        if not tokens:
            return []

        # Term frequency
        tf: Counter = Counter(tokens)
        total = len(tokens)

        # Treat the entire document as a single "document" for IDF – we
        # use sentence-level IDF to give more weight to rarer terms.
        sentences = re.split(r"[.!?]+", text.lower())
        doc_freq: Counter = Counter()
        for sentence in sentences:
            sentence_tokens = set(self._tokenise(sentence))
            for tok in sentence_tokens:
                doc_freq[tok] += 1

        n_sentences = max(len(sentences), 1)
        tfidf_scores: Dict[str, float] = {}
        for term, count in tf.items():
            tf_score = count / total
            idf_score = math.log((1 + n_sentences) / (1 + doc_freq.get(term, 0))) + 1.0
            tfidf_scores[term] = tf_score * idf_score

        ranked = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)
        return [term for term, _ in ranked[:top_n]]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenise(text: str) -> List[str]:
        """Lowercase, remove punctuation, and filter stop-words."""
        text = text.lower()
        # Remove punctuation
        text = text.translate(str.maketrans("", "", string.punctuation))
        tokens = text.split()
        return [
            t for t in tokens
            if t and t not in _STOP_WORDS and len(t) > 2 and not t.isdigit()
        ]