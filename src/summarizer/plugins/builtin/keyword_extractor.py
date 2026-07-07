"""Built-in post-processor: extracts top-N keywords from the original article.

Uses a lightweight TF-IDF approach (no external ML dependencies required).
If ``nltk`` is installed the stop-word list is enriched; otherwise a small
built-in stop-word list is used as a fallback.
"""

from __future__ import annotations

import math
import re
import string
from collections import Counter
from typing import Any, Dict, FrozenSet, List, Optional

from ..base import BasePostProcessor

# ---------------------------------------------------------------------------
# Stop-word handling
# ---------------------------------------------------------------------------

_BUILTIN_STOPWORDS: FrozenSet[str] = frozenset(
    """
    a about above after again against all am an and any are aren't as at be
    because been before being below between both but by can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further get got had hadn't has hasn't have haven't having he he'd
    he'll he's her here here's hers herself him himself his how how's i i'd
    i'll i'm i've if in into is isn't it it's its itself let's me more most
    mustn't my myself no nor not of off on once only or other ought our ours
    ourselves out over own same shan't she she'd she'll she's should shouldn't
    so some such than that that's the their theirs them themselves then there
    there's these they they'd they'll they're they've this those through to too
    under until up very was wasn't we we'd we'll we're we've were weren't what
    what's when when's where where's which while who who's whom why why's will
    with won't would wouldn't you you'd you'll you're you've your yours yourself
    yourselves
    """.split()
)


def _get_stopwords() -> FrozenSet[str]:
    try:
        import nltk  # type: ignore[import-untyped]

        try:
            from nltk.corpus import stopwords  # type: ignore[import-untyped]

            return frozenset(stopwords.words("english"))
        except LookupError:
            nltk.download("stopwords", quiet=True)
            from nltk.corpus import stopwords  # type: ignore[import-untyped]

            return frozenset(stopwords.words("english"))
    except ImportError:
        return _BUILTIN_STOPWORDS


# ---------------------------------------------------------------------------
# TF-IDF helpers
# ---------------------------------------------------------------------------


def _tokenise(text: str) -> List[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return re.split(r"\s+", text.strip())


def _term_frequency(tokens: List[str]) -> Dict[str, float]:
    count = Counter(tokens)
    total = max(len(tokens), 1)
    return {word: freq / total for word, freq in count.items()}


def _idf(word: str, documents: List[List[str]]) -> float:
    """Inverse document frequency across a pseudo-corpus.

    We treat the article as sentence-level 'documents' for better IDF signal.
    """
    containing = sum(1 for doc in documents if word in doc)
    return math.log((len(documents) + 1) / (containing + 1)) + 1.0


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Return the top-*n* keywords from *text* using a TF-IDF heuristic."""
    stopwords = _get_stopwords()

    # Split into sentences to build a small pseudo-corpus
    sentences = re.split(r"[.!?]\s+", text)
    docs: List[List[str]] = [
        [w for w in _tokenise(s) if w and w not in stopwords] for s in sentences
    ]

    all_tokens = [w for doc in docs for w in doc]
    tf = _term_frequency(all_tokens)

    scored: Dict[str, float] = {}
    for word in tf:
        if len(word) < 3:
            continue
        scored[word] = tf[word] * _idf(word, docs)

    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in ranked[:top_n]]


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------


class KeywordExtractor(BasePostProcessor):
    """Extracts the top-N keywords from the *original article text* and stores
    them in ``summary.metadata["keywords"]``.

    Configuration
    -------------
    Pass keyword arguments to ``__init__`` when instantiating manually::

        extractor = KeywordExtractor(top_n=15)

    The registry instantiates with defaults; to customise the behaviour
    subclass this processor.
    """

    name = "keyword_extractor"
    description = "Extracts top-N TF-IDF keywords from the original article text."
    version = "1.0.0"

    def __init__(self, top_n: int = 10) -> None:
        self.top_n = top_n

    def process(self, summary: Any, article_text: str = "") -> Any:
        """Attach a ``keywords`` list to ``summary.metadata``."""
        source = article_text or getattr(summary, "text", "") or ""
        keywords = extract_keywords(source, top_n=self.top_n)

        # Support both dataclass (mutable) and Pydantic models
        try:
            # Pydantic v2 model_copy
            existing_meta: Dict[str, Any] = dict(getattr(summary, "metadata", {}) or {})
            existing_meta["keywords"] = keywords
            summary = summary.model_copy(update={"metadata": existing_meta})
        except AttributeError:
            try:
                if not hasattr(summary, "metadata") or summary.metadata is None:
                    summary.metadata = {}
                summary.metadata["keywords"] = keywords
            except (AttributeError, TypeError):
                pass  # Best-effort; do not crash the pipeline.

        return summary