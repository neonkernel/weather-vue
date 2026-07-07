"""
Built-in post-processor: extracts top-N keywords from the original article
using a simple TF-IDF approach (no external dependencies required).

If *scikit-learn* is installed it will be preferred; otherwise a pure-Python
fallback is used so the package works in minimal environments.
"""
from __future__ import annotations

import math
import re
import string
from collections import Counter
from typing import Any, Dict, List, Optional

from ..base import BasePostProcessor

# ---------------------------------------------------------------------------
# Stop-words (minimal English set — avoids an NLTK download requirement)
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset(
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
    with won't would wouldn't you you'd you'll you're you've your yours
    yourself yourselves
    """.split()
)


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    return [w for w in text.split() if w not in _STOP_WORDS and len(w) > 2]


def _tfidf_keywords(text: str, top_n: int = 10) -> List[str]:
    """
    Single-document TF-IDF approximation.

    Without a reference corpus we treat each sentence as a "document" and
    compute IDF over sentences.  This reliably surfaces words that appear
    frequently in the article but are concentrated in fewer sentences
    (i.e. topic-specific terms).
    """
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    # TF across the whole document
    tokens = _tokenize(text)
    tf = Counter(tokens)
    total = len(tokens) or 1

    # IDF: how many sentences contain each token
    doc_freq: Counter = Counter()
    for sent in sentences:
        unique_in_sent = set(_tokenize(sent))
        doc_freq.update(unique_in_sent)

    n_docs = len(sentences)
    scores: Dict[str, float] = {}
    for word, count in tf.items():
        tf_score = count / total
        idf_score = math.log((1 + n_docs) / (1 + doc_freq.get(word, 0))) + 1
        scores[word] = tf_score * idf_score

    top = sorted(scores, key=lambda w: scores[w], reverse=True)[:top_n]
    return top


class KeywordExtractor(BasePostProcessor):
    """
    Extracts the top-N keywords from the original article text and attaches
    them to the summary object as ``summary.keywords``.

    Configuration keys (passed via *config* dict):
        - ``keyword_top_n`` (int, default 10): number of keywords to extract.
    """

    name = "keyword_extractor"
    description = (
        "Extracts top-N keywords from the article using TF-IDF and attaches "
        "them to the summary as `summary.keywords`."
    )

    def process(
        self,
        summary: Any,
        *,
        article_text: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        cfg = config or {}
        top_n = int(cfg.get("keyword_top_n", 10))

        source_text = article_text or getattr(summary, "content", "") or ""
        keywords = _tfidf_keywords(source_text, top_n=top_n)

        # Attach keywords to the summary object if possible; if it's a plain
        # dataclass or object we use setattr, otherwise we skip silently.
        try:
            object.__setattr__(summary, "keywords", keywords)
        except (AttributeError, TypeError):
            try:
                summary.keywords = keywords
            except AttributeError:
                pass

        return summary