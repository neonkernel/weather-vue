"""Helper functions for token counting and cost estimation."""

import tiktoken
from typing import Optional

# Cost per 1K tokens (in USD) for supported models
# Prices as of 2024 - update as needed
MODEL_COSTS = {
    "gpt-4o-mini": {"prompt": 0.000150, "completion": 0.000600},  # per 1K tokens
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
}

# Context window sizes (in tokens) for supported models
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
}

# Reserve tokens for system prompt + response
RESERVED_TOKENS = 2_000


def get_encoding(model: str) -> tiktoken.Encoding:
    """Get the tiktoken encoding for a given model."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to cl100k_base for unknown models (used by GPT-4 family)
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count the number of tokens in a text string for a given model.

    Args:
        text: The text to count tokens for.
        model: The model name to use for tokenization.

    Returns:
        The number of tokens in the text.
    """
    encoding = get_encoding(model)
    return len(encoding.encode(text))


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "gpt-4o-mini",
) -> float:
    """Estimate the cost of an API call in USD.

    Args:
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        model: The model name.

    Returns:
        Estimated cost in USD.
    """
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
    prompt_cost = (prompt_tokens / 1000) * costs["prompt"]
    completion_cost = (completion_tokens / 1000) * costs["completion"]
    return prompt_cost + completion_cost


def get_context_window(model: str) -> int:
    """Get the context window size for a model.

    Args:
        model: The model name.

    Returns:
        Context window size in tokens.
    """
    return MODEL_CONTEXT_WINDOWS.get(model, 128_000)


def fits_in_context(
    text: str,
    model: str = "gpt-4o-mini",
    reserved_tokens: int = RESERVED_TOKENS,
) -> bool:
    """Check if a text fits within the model's context window.

    Args:
        text: The text to check.
        model: The model name.
        reserved_tokens: Tokens to reserve for system prompt and response.

    Returns:
        True if the text fits in the context window, False otherwise.
    """
    token_count = count_tokens(text, model)
    context_window = get_context_window(model)
    available_tokens = context_window - reserved_tokens
    return token_count <= available_tokens


def get_available_tokens(model: str = "gpt-4o-mini", reserved_tokens: int = RESERVED_TOKENS) -> int:
    """Get the number of tokens available for content given a model and reserved tokens.

    Args:
        model: The model name.
        reserved_tokens: Tokens to reserve for system prompt and response.

    Returns:
        Number of available tokens for content.
    """
    context_window = get_context_window(model)
    return context_window - reserved_tokens