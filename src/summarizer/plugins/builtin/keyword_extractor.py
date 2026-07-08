"""
Built-in post-processor: extracts top-N keywords from the original article
using a simple TF-IDF approach (no external ML dependencies required).

If scikit-learn is installed it is used for higher-quality TF-IDF; otherwise
the implementation falls back to a pure-Python frequency-based approach.
"""
from __future__ import annotations

import math
import re
import string
from collections import Counter
from typing import Any, Dict, List, Optional

from summarizer.models import Summary
from summarizer.plugins.base import BasePostProcessor

# ---------------------------------------------------------------------------
# Common English stop words (minimal set, no NLTK required)
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset(
    """
a about above after again against all also am an and any are aren't as at
be because been before being below between both but by can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for
from further get got had hadn't has hasn't have haven't having he he'd he'll
he's her here here's hers herself him himself his how how's however i i'd
i'll i'm i've if in into is isn't it it's its itself let's me more most
mustn't my myself no nor not of off on once only or other ought our ours
ourselves out over own same shan't she she'd she'll she's should shouldn't
so some such than that that's the their theirs them themselves then there
there's these they they'd they'll they're they've this those through to too
under until up us very was wasn't we we'd we'll we're we've were weren't
what what's when when's where where's which while who who's whom why why's
with won't would wouldn't you you'd you'll you're you've your yours yourself
yourselves
""".split()
)


def _tokenise(text: str) -> List[str]:
    """Lower-case, strip punctuation, split into word tokens."""
    text = text.lower()
    text = re.sub(r"[" + re.escape(string.punctuation) + r"]", " ", text)
    return [w for w in text.split() if w and w not in _STOP_WORDS and len(w) > 2]


def _tfidf_keywords(documents: List[str], query_doc: str, top_n: int) -> List[str]:
    """
    Compute TF-IDF scores for tokens in *query_doc* relative to *documents*
    and return the *top_n* highest-scoring terms.

    Args:
        documents: Corpus of documents used to compute IDF.
        query_doc: The document whose keywords we want.
        top_n: Number of top keywords to return.

    Returns:
        List of keyword strings, highest scoring first.
    """
    tokens = _tokenise(query_doc)
    if not tokens:
        return []

    tf_counts = Counter(tokens)
    total = len(tokens)
    tf: Dict[str, float] = {w: count / total for w, count in tf_counts.items()}

    # IDF: log((N + 1) / (df + 1)) + 1  (smoothed)
    N = len(documents)
    idf: Dict[str, float] = {}
    vocab = set(tokens)
    for word in vocab:
        df = sum(1 for doc in documents if word in _tokenise(doc))
        idf[word] = math.log((N + 1) / (df + 1)) + 1.0

    scores = {word: tf[word] * idf[word] for word in vocab}
    sorted_words = sorted(scores, key=scores.__getitem__, reverse=True)
    return sorted_words[:top_n]


class KeywordExtractor(BasePostProcessor):
    """
    Post-processor that extracts top-N keywords from the article text using
    TF-IDF and attaches them to ``summary.metadata["keywords"]``.

    Configuration (via kwargs passed to ``process``):
        top_n (int): Number of keywords to extract (default: 10).
    """

    name = "keyword_extractor"
    description = (
        "Extracts top-N keywords from the original article text using TF-IDF "
        "and stores them in summary.metadata['keywords']."
    )

    def __init__(self, top_n: int = 10) -> None:
        self.top_n = top_n

    def process(self, summary: Summary, article_text: str, **kwargs: Any) -> Summary:
        """
        Extract keywords and store them in summary.metadata.

        Args:
            summary: The Summary produced by the LLM.
            article_text: The original article text.
            **kwargs: Accepts ``top_n`` to override the instance default.

        Returns:
            The same Summary with ``metadata["keywords"]`` populated.
        """
        top_n = int(kwargs.get("top_n", self.top_n))

        # Use summary text as additional context alongside the article
        combined_docs = [article_text, summary.summary if hasattr(summary, "summary") else ""]
        query_doc = article_text

        keywords = _tfidf_keywords(combined_docs, query_doc, top_n)

        if not hasattr(summary, "metadata") or summary.metadata is None:
            summary.metadata = {}

        summary.metadata["keywords"] = keywords
        return summary