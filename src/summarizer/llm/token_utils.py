"""Helper functions for token counting, cost estimation, and context window checks."""

import tiktoken

# Model context window sizes (in tokens)
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
}

# Cost per 1K tokens (prompt, completion) in USD
MODEL_COSTS = {
    "gpt-4o-mini": (0.000150, 0.000600),   # $0.15/1M input, $0.60/1M output
    "gpt-4o": (0.005, 0.015),               # $5/1M input, $15/1M output
    "gpt-4-turbo": (0.010, 0.030),
    "gpt-4": (0.030, 0.060),
    "gpt-3.5-turbo": (0.0005, 0.0015),
}

# Reserve tokens for the response + system prompt overhead
RESPONSE_RESERVE_TOKENS = 1_000
SYSTEM_PROMPT_OVERHEAD = 500


def get_encoding(model: str) -> tiktoken.Encoding:
    """Get the tiktoken encoding for a given model."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to cl100k_base for unknown models (GPT-4/3.5 compatible)
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
    if model not in MODEL_COSTS:
        # Use gpt-4o-mini costs as a default
        prompt_cost_per_k, completion_cost_per_k = MODEL_COSTS["gpt-4o-mini"]
    else:
        prompt_cost_per_k, completion_cost_per_k = MODEL_COSTS[model]

    prompt_cost = (prompt_tokens / 1_000) * prompt_cost_per_k
    completion_cost = (completion_tokens / 1_000) * completion_cost_per_k
    return prompt_cost + completion_cost


def get_context_window(model: str) -> int:
    """Get the context window size for a given model.

    Args:
        model: The model name.

    Returns:
        The context window size in tokens.
    """
    return MODEL_CONTEXT_WINDOWS.get(model, 128_000)


def fits_in_context(
    text: str,
    model: str = "gpt-4o-mini",
    reserved_tokens: int = RESPONSE_RESERVE_TOKENS + SYSTEM_PROMPT_OVERHEAD,
) -> bool:
    """Check whether a text fits within the model's context window.

    Args:
        text: The text to check.
        model: The model name.
        reserved_tokens: Tokens to reserve for system prompt and response.

    Returns:
        True if the text fits within the available context window.
    """
    token_count = count_tokens(text, model)
    available_tokens = get_context_window(model) - reserved_tokens
    return token_count <= available_tokens


def max_chunk_tokens(
    model: str = "gpt-4o-mini",
    reserved_tokens: int = RESPONSE_RESERVE_TOKENS + SYSTEM_PROMPT_OVERHEAD,
) -> int:
    """Get the maximum number of tokens available for a chunk of text.

    Args:
        model: The model name.
        reserved_tokens: Tokens to reserve for system prompt and response.

    Returns:
        The maximum number of tokens for a text chunk.
    """
    return get_context_window(model) - reserved_tokens