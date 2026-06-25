"""Helper functions for token counting and cost estimation."""

import logging
from functools import lru_cache
from typing import Optional

import tiktoken

logger = logging.getLogger(__name__)

# Cost per 1K tokens (USD) — prices as of mid-2024
# Format: (prompt_cost_per_1k, completion_cost_per_1k)
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.000150, 0.000600),
    "gpt-4o": (0.005, 0.015),
    "gpt-4-turbo": (0.010, 0.030),
    "gpt-4": (0.030, 0.060),
    "gpt-3.5-turbo": (0.0005, 0.0015),
}

# Context window sizes (in tokens)
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
}

# Safe threshold: leave room for system prompt + response
CONTEXT_SAFETY_MARGIN = 0.85


@lru_cache(maxsize=4)
def _get_encoding(model: str) -> tiktoken.Encoding:
    """Get (and cache) the tiktoken encoding for a model."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(
            "No specific encoding found for model '%s'; falling back to cl100k_base.",
            model,
        )
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Count the number of tokens in *text* for the given *model*.

    Args:
        text: The text to tokenize.
        model: The OpenAI model name (used to select the correct tokenizer).

    Returns:
        Integer token count.
    """
    if not text:
        return 0
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "gpt-4o-mini",
) -> float:
    """
    Estimate the USD cost of an API call.

    Args:
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        model: The OpenAI model name.

    Returns:
        Estimated cost in USD.
    """
    prompt_rate, completion_rate = MODEL_COSTS.get(
        model, MODEL_COSTS["gpt-4o-mini"]
    )
    cost = (prompt_tokens / 1_000 * prompt_rate) + (
        completion_tokens / 1_000 * completion_rate
    )
    return cost


def fits_in_context(
    text: str,
    model: str = "gpt-4o-mini",
    reserved_tokens: int = 1_000,
) -> bool:
    """
    Determine whether *text* fits within the model's context window.

    A safety margin is applied so there is always room for the system
    prompt, the user instruction, and the model's response.

    Args:
        text: The article text to check.
        model: The OpenAI model name.
        reserved_tokens: Additional tokens to reserve (e.g. for system
            prompt and completion).

    Returns:
        True if the text fits; False if chunking is required.
    """
    context_window = MODEL_CONTEXT_WINDOWS.get(
        model, MODEL_CONTEXT_WINDOWS["gpt-4o-mini"]
    )
    usable_tokens = int(context_window * CONTEXT_SAFETY_MARGIN) - reserved_tokens
    token_count = count_tokens(text, model)
    return token_count <= usable_tokens


def get_context_window(model: str = "gpt-4o-mini") -> int:
    """Return the context window size for *model* in tokens."""
    return MODEL_CONTEXT_WINDOWS.get(model, MODEL_CONTEXT_WINDOWS["gpt-4o-mini"])