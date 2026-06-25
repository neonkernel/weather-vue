"""Helper functions for token counting and cost estimation."""

import tiktoken

# Pricing per 1K tokens (as of 2024, subject to change)
MODEL_PRICING = {
    "gpt-4o-mini": {"prompt": 0.000150, "completion": 0.000600},
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-3.5-turbo": {"prompt": 0.001, "completion": 0.002},
}

# Context window sizes in tokens
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
}

# Default encoding fallback
DEFAULT_ENCODING = "cl100k_base"


def _get_encoding(model: str) -> tiktoken.Encoding:
    """Get the tiktoken encoding for a given model."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding(DEFAULT_ENCODING)


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Count the number of tokens in a text string for a given model.

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
    model: str = "gpt-4o-mini",
) -> float:
    """
    Estimate the cost of an API call in USD.

    Args:
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        model: The model name used for the call.

    Returns:
        Estimated cost in USD.
    """
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        # Fall back to gpt-4o-mini pricing if model not found
        pricing = MODEL_PRICING["gpt-4o-mini"]

    prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
    completion_cost = (completion_tokens / 1000) * pricing["completion"]
    return prompt_cost + completion_cost


def fits_in_context(
    text: str,
    model: str = "gpt-4o-mini",
    reserved_tokens: int = 1000,
) -> bool:
    """
    Check if a text fits within the model's context window.

    Args:
        text: The text to check.
        model: The model name to check against.
        reserved_tokens: Number of tokens to reserve for system prompt,
                         user instructions, and completion output.

    Returns:
        True if the text fits within the context window, False otherwise.
    """
    context_window = MODEL_CONTEXT_WINDOWS.get(model, 128_000)
    token_count = count_tokens(text, model)
    return token_count + reserved_tokens <= context_window


def get_context_window(model: str = "gpt-4o-mini") -> int:
    """
    Get the context window size for a model.

    Args:
        model: The model name.

    Returns:
        Context window size in tokens.
    """
    return MODEL_CONTEXT_WINDOWS.get(model, 128_000)