"""Helper functions for token counting and cost estimation."""

from __future__ import annotations

import logging

import tiktoken

logger = logging.getLogger(__name__)

# Cost per 1,000 tokens (as of 2024 — update as pricing changes)
MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
}

# Context window sizes in tokens
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
}

DEFAULT_MODEL = "gpt-4o-mini"
# Reserve tokens for system prompt + response
RESERVED_TOKENS = 2_000


def _get_encoding(model: str) -> tiktoken.Encoding:
    """Get the tiktoken encoding for a model, with fallback."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(
            "No encoding found for model '%s', falling back to cl100k_base.", model
        )
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """Count the number of tokens in a text string for the given model.

    Args:
        text: The text to count tokens for.
        model: The model name to use for tokenization.

    Returns:
        The number of tokens in the text.
    """
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = DEFAULT_MODEL,
) -> float:
    """Estimate the cost in USD for a given number of tokens.

    Args:
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        model: The model name to use for cost estimation.

    Returns:
        Estimated cost in USD.
    """
    costs = MODEL_COSTS.get(model)
    if costs is None:
        logger.warning(
            "No cost data for model '%s'. Returning 0.0.", model
        )
        return 0.0

    prompt_cost = (prompt_tokens / 1_000) * costs["prompt"]
    completion_cost = (completion_tokens / 1_000) * costs["completion"]
    return prompt_cost + completion_cost


def get_context_window(model: str = DEFAULT_MODEL) -> int:
    """Get the context window size in tokens for a model.

    Args:
        model: The model name.

    Returns:
        Context window size in tokens.
    """
    return MODEL_CONTEXT_WINDOWS.get(model, 8_192)


def fits_in_context(
    text: str,
    model: str = DEFAULT_MODEL,
    reserved_tokens: int = RESERVED_TOKENS,
) -> bool:
    """Check if a text fits within a model's context window.

    Args:
        text: The text to check.
        model: The model name.
        reserved_tokens: Tokens to reserve for system prompt and response.

    Returns:
        True if the text fits in the context window.
    """
    token_count = count_tokens(text, model)
    available = get_context_window(model) - reserved_tokens
    return token_count <= available