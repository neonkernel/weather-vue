"""Top-level orchestration: takes an Article, returns a Summary."""

from __future__ import annotations

import logging

from src.summarizer.config import Config
from src.summarizer.llm.client import SummarizerClient
from src.summarizer.llm.prompts import SummaryStyle
from src.summarizer.models import Article, Summary

logger = logging.getLogger(__name__)


def summarize(
    article: Article,
    config: Config | None = None,
    style: SummaryStyle = SummaryStyle.CONCISE,
) -> Summary:
    """Summarize the given *article* and return a :class:`Summary`.

    Parameters
    ----------
    article:
        The article to summarize.
    config:
        Optional :class:`Config` instance.  A default one is created if not
        provided.
    style:
        The summary style (concise, detailed, bullet_points, executive).

    Returns
    -------
    Summary
        The populated summary dataclass.
    """
    cfg = config or Config()
    client = SummarizerClient(config=cfg, style=style)

    title = getattr(article, "title", "") or ""
    text = article.text

    if not text or not text.strip():
        logger.warning("Article '%s' has no text; returning empty summary.", title)
        return Summary(
            title=title,
            summary="",
            model=cfg.model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost=0.0,
        )

    logger.info("Starting summarization for article: '%s'", title)
    summary = client.summarize(text, title=title)
    logger.info(
        "Summarization complete for '%s' — %d total tokens used, cost=$%.6f",
        title,
        summary.total_tokens,
        summary.estimated_cost,
    )
    return summary