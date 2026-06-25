"""Top-level orchestration for article summarization."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .llm import SummarizerClient
from .llm.chunker import TextChunker, MapReduceSummarizer
from .llm.prompts import PromptBuilder, SummaryStyle
from .llm.token_utils import count_tokens, estimate_cost, fits_in_context
from .models import Article, Summary

logger = logging.getLogger(__name__)


def summarize(
    article: Article,
    client: Optional[SummarizerClient] = None,
    style: SummaryStyle = SummaryStyle.CONCISE,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 1024,
    chunk_size: Optional[int] = None,
    overlap_tokens: int = 100,
    api_key: Optional[str] = None,
) -> Summary:
    """
    Summarize an article using the LLM.

    Automatically decides whether to use direct summarization or
    map-reduce chunking based on the article's token count.

    Args:
        article: The Article to summarize.
        client: Optional pre-configured SummarizerClient. If not provided,
                one will be created using the other parameters.
        style: The summary style to use.
        model: The LLM model to use.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens for completion output.
        chunk_size: Maximum tokens per chunk (for long articles).
        overlap_tokens: Token overlap between chunks.
        api_key: OpenAI API key (falls back to OPENAI_API_KEY env var).

    Returns:
        A Summary dataclass with the generated summary and metadata.

    Raises:
        ValueError: If no API key is available.
        openai.OpenAIError: If the API call fails after retries.
    """
    if client is None:
        client = SummarizerClient(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    prompt_builder = PromptBuilder(style=style)
    chunker = TextChunker(
        model=model,
        chunk_size=chunk_size,
        overlap_tokens=overlap_tokens,
        reserved_tokens=max_tokens + 500,  # Reserve space for completion + system prompt
    )

    article_text = article.content
    token_count = count_tokens(article_text, model)

    logger.info(
        f"Starting summarization: title='{article.title}', "
        f"tokens={token_count}, style={style.value}, model={model}"
    )

    use_chunking = chunker.needs_chunking(article_text)

    if use_chunking:
        logger.info(
            f"Article exceeds chunk size ({token_count} tokens); "
            f"using map-reduce summarization"
        )
        map_reduce = MapReduceSummarizer(
            client=client,
            prompt_builder=prompt_builder,
            chunker=chunker,
        )
        summary_text, usage = map_reduce.summarize(article_text)
        method = "map_reduce"
    else:
        logger.info(
            f"Article fits in context ({token_count} tokens); "
            f"using direct summarization"
        )
        messages = prompt_builder.build_messages(article_text)
        summary_text, usage = client.complete(messages)
        method = "direct"

    # Calculate estimated cost
    estimated_cost = estimate_cost(
        usage["prompt_tokens"],
        usage["completion_tokens"],
        model,
    )

    summary = Summary(
        title=article.title,
        url=article.url,
        summary=summary_text,
        style=style.value,
        model=model,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
        estimated_cost_usd=estimated_cost,
        method=method,
        created_at=datetime.now(timezone.utc),
    )

    logger.info(
        f"Summarization complete: method={method}, "
        f"total_tokens={usage['total_tokens']}, "
        f"estimated_cost=${estimated_cost:.6f}"
    )

    return summary