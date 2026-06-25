"""Top-level orchestration: takes an Article, returns a Summary."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from .config import Config
from .llm import SummarizerClient
from .llm.prompts import SummaryStyle
from .models import Article, Summary

logger = logging.getLogger(__name__)


def summarize(
    article: Article,
    config: Config | None = None,
    style: SummaryStyle = "concise",
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    extra_instructions: str = "",
) -> Summary:
    """Summarize an *Article* and return a *Summary* dataclass.

    Args:
        article: The article to summarize.
        config: Optional Config instance; falls back to defaults if not provided.
        style: One of 'concise', 'detailed', or 'bullet'.
        model: Override the model specified in config.
        temperature: Override the sampling temperature.
        max_tokens: Override the maximum completion tokens.
        extra_instructions: Additional freeform instructions appended to the system prompt.

    Returns:
        A populated Summary dataclass.

    Raises:
        ValueError: If the article has no content to summarize.
        openai.OpenAIError: On unrecoverable API errors (after retries are exhausted).
    """
    if not article.content or not article.content.strip():
        raise ValueError(f"Article '{article.url}' has no content to summarize.")

    cfg = config or Config()

    resolved_model = model or getattr(cfg, "model", "gpt-4o-mini")
    resolved_temperature = temperature if temperature is not None else getattr(cfg, "temperature", 0.3)
    resolved_max_tokens = max_tokens or getattr(cfg, "max_tokens", 1_024)
    api_key = getattr(cfg, "openai_api_key", None)

    logger.info(
        "Starting summarization — url=%s model=%s style=%s",
        article.url,
        resolved_model,
        style,
    )

    client = SummarizerClient(
        api_key=api_key,
        model=resolved_model,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
        style=style,
        extra_instructions=extra_instructions,
    )

    summary_text, usage = client.summarize(article.content)

    summary = Summary(
        url=article.url,
        title=article.title,
        summary=summary_text,
        model=resolved_model,
        style=style,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        created_at=datetime.now(tz=timezone.utc),
    )

    logger.info(
        "Summarization complete — url=%s tokens_used=%d",
        article.url,
        usage.get("total_tokens", 0),
    )

    return summary