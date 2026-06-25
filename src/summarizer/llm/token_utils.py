"""Helper functions for token counting and cost estimation."""

from __future__ import annotations

import logging

import tiktoken

logger = logging.getLogger(__name__)

# Cost per 1K tokens in USD (approximate, as of mid-2025)
MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"prompt": 0.000150, "completion": 0.000600},
    "gpt-4o": {"prompt": 0.005000, "completion": 0.015000},
    "gpt-4-turbo": {"prompt": 0.010000, "completion": 0.030000},
    "gpt-3.5-turbo": {"prompt": 0.000500, "completion": 0.001500},
}

# Context window sizes (in tokens)
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-3.5-turbo": 16_385,
}

DEFAULT_MODEL = "gpt-4o-mini"
# Reserve tokens for system prompt, user instruction, and response
RESERVED_TOKENS = 2_000


def _get_encoding(model: str) -> tiktoken.Encoding:
    """Return the tiktoken encoding for a given model, falling back gracefully."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(
            "No tiktoken encoding found for model '%s'; falling back to cl100k_base.",
            model,
        )
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """Count the number of tokens in *text* for the given *model*."""
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = DEFAULT_MODEL,
) -> float:
    """Estimate the USD cost for a single API call.

    Returns 0.0 if the model pricing is unknown.
    """
    costs = MODEL_COSTS.get(model)
    if costs is None:
        logger.warning("No cost data for model '%s'; returning 0.0.", model)
        return 0.0
    prompt_cost = (prompt_tokens / 1_000) * costs["prompt"]
    completion_cost = (completion_tokens / 1_000) * costs["completion"]
    return prompt_cost + completion_cost


def fits_in_context(
    text: str,
    model: str = DEFAULT_MODEL,
    reserved_tokens: int = RESERVED_TOKENS,
) -> bool:
    """Return True if *text* fits within the model's usable context window."""
    max_tokens = MODEL_CONTEXT_WINDOWS.get(model, 8_192)
    usable = max_tokens - reserved_tokens
    token_count = count_tokens(text, model)
    return token_count <= usable


def max_content_tokens(model: str = DEFAULT_MODEL, reserved_tokens: int = RESERVED_TOKENS) -> int:
    """Return the maximum number of tokens available for article content."""
    return MODEL_CONTEXT_WINDOWS.get(model, 8_192) - reserved_tokens