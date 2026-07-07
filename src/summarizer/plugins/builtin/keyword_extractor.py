"""Built-in post-processor: extracts top-N keywords from the article using TF-IDF."""

from __future__ import annotations

import math
import re
import string
from collections import Counter
from typing import List

from summarizer.plugins.base import BasePostProcessor

# ---------------------------------------------------------------------------
# Stop-words (minimal English set; avoids an NLTK dependency)
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "its", "this", "that", "was",
        "are", "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "shall", "can",
        "not", "as", "if", "so", "then", "than", "also", "more", "most",
        "about", "up", "out", "into", "through", "during", "before", "after",
        "each", "which", "who", "whom", "there", "their", "they", "we", "you",
        "he", "she", "i", "me", "my", "your", "our", "us", "him", "her", "his",
        "just", "some", "any", "all", "both", "few", "no", "nor", "only", "own",
        "same", "other", "such", "s", "t", "re", "ve", "ll", "d", "m",
    }
)


def _tokenize(text: str) -> List[str]:
    """Lower-case, strip punctuation, split on whitespace."""
    text = text.lower()
    text = re.sub(r"[" + re.escape(string.punctuation) + r"]", " ", text)
    return [w for w in text.split() if w and w not in _STOP_WORDS and len(w) > 2]


def _tf(tokens: List[str]) -> Counter:
    counts = Counter(tokens)
    total = len(tokens) or 1
    return Counter({w: c / total for w, c in counts.items()})


def _idf(word: str, documents: List[List[str]]) -> float:
    n_docs = len(documents)
    n_containing = sum(1 for doc in documents if word in doc)
    return math.log((n_docs + 1) / (n_containing + 1)) + 1.0


def extract_keywords(texts: List[str], top_n: int = 10) -> List[str]:
    """Return the top *top_n* keywords across the provided *texts* using TF-IDF.

    Parameters
    ----------
    texts:
        List of text documents (e.g. article text + summary text).
    top_n:
        Number of keywords to return.
    """
    tokenized = [_tokenize(t) for t in texts]
    if not any(tokenized):
        return []

    # Score each unique word by its average TF-IDF across documents
    vocab = set(w for doc in tokenized for w in doc)
    scores: dict[str, float] = {}
    for word in vocab:
        tf_scores = [_tf(doc).get(word, 0.0) for doc in tokenized]
        idf_score = _idf(word, tokenized)
        scores[word] = (sum(tf_scores) / len(tf_scores)) * idf_score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in ranked[:top_n]]


class KeywordExtractor(BasePostProcessor):
    """Extracts the top N keywords from the article text and attaches them to the summary.

    The keywords are stored in ``summary.metadata["keywords"]`` as a list of strings.
    """

    name = "keyword_extractor"
    description = (
        "Extracts top-N keywords from the article using TF-IDF "
        "and stores them in summary.metadata['keywords']."
    )

    def __init__(self, top_n: int = 10) -> None:
        self.top_n = top_n

    def process(self, summary, article_text: str):  # type: ignore[override]
        """Attach keywords to *summary*.metadata and return the summary."""
        texts = [article_text]
        # Also include the summary text itself if available
        summary_text = getattr(summary, "summary", "") or ""
        if summary_text:
            texts.append(summary_text)

        keywords = extract_keywords(texts, top_n=self.top_n)

        # Attach to metadata dict (create if absent)
        if not hasattr(summary, "metadata") or summary.metadata is None:
            try:
                summary.metadata = {}
            except AttributeError:
                pass

        try:
            summary.metadata["keywords"] = keywords
        except (AttributeError, TypeError):
            pass  # Model doesn't support metadata mutation; skip silently

        return summary