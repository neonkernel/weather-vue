"""Helper functions for token counting, cost estimation, and context window checks."""

from __future__ import annotations

import logging

import tiktoken

logger = logging.getLogger(__name__)

# Context window sizes (in tokens) for supported models
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
}

# Cost per 1k tokens (prompt, completion) in USD
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.000150, 0.000600),   # $0.15 / $0.60 per 1M tokens
    "gpt-4o": (0.005, 0.015),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4": (0.03, 0.06),
    "gpt-3.5-turbo": (0.0005, 0.0015),
}

_ENCODER_CACHE: dict[str, tiktoken.Encoding] = {}


def _get_encoder(model: str) -> tiktoken.Encoding:
    """Return (and cache) a tiktoken encoder for the given model."""
    if model not in _ENCODER_CACHE:
        try:
            _ENCODER_CACHE[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fall back to cl100k_base for unknown models
            logger.warning(
                "No tiktoken encoding found for model '%s'; falling back to cl100k_base.",
                model,
            )
            _ENCODER_CACHE[model] = tiktoken.get_encoding("cl100k_base")
    return _ENCODER_CACHE[model]


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Return the number of tokens in *text* for the given *model*."""
    encoder = _get_encoder(model)
    return len(encoder.encode(text))


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "gpt-4o-mini",
) -> float:
    """Estimate the USD cost for a single API call.

    Returns 0.0 if the model is not in the cost table.
    """
    if model not in MODEL_COSTS:
        logger.warning("Cost data not available for model '%s'.", model)
        return 0.0
    prompt_cost_per_k, completion_cost_per_k = MODEL_COSTS[model]
    cost = (prompt_tokens / 1000 * prompt_cost_per_k) + (
        completion_tokens / 1000 * completion_cost_per_k
    )
    return round(cost, 8)


def fits_in_context(
    text: str,
    model: str = "gpt-4o-mini",
    reserved_tokens: int = 1_000,
) -> bool:
    """Return True if *text* fits within the model's context window.

    *reserved_tokens* are subtracted from the context window to leave room for
    system / user prompt overhead and the completion.
    """
    context_window = MODEL_CONTEXT_WINDOWS.get(model, 4_096)
    available = context_window - reserved_tokens
    token_count = count_tokens(text, model)
    return token_count <= available


def get_context_window(model: str) -> int:
    """Return the context window size for the given model (defaults to 4096)."""
    return MODEL_CONTEXT_WINDOWS.get(model, 4_096)