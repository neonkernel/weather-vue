"""
Configuration management for the summarizer package.

Loads environment variables from a .env file (if present) and exposes
them as a validated Config dataclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from summarizer.logger import get_logger

logger = get_logger("config")

# Load .env from the current working directory (or any parent) on import.
load_dotenv(override=False)


@dataclass
class Config:
    """Validated runtime configuration."""

    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    timeout: int = 30

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_env(cls) -> "Config":
        """
        Build a Config instance from environment variables.

        Environment variables:
            OPENAI_API_KEY      — required; OpenAI secret key.
            SUMMARIZER_MODEL    — optional; model name (default: gpt-4o-mini).
            SUMMARIZER_MAX_TOKENS — optional; int (default: 1024).
            SUMMARIZER_TIMEOUT  — optional; int seconds (default: 30).

        Raises:
            ConfigError: if a required variable is missing or a value is invalid.
        """
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ConfigError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or export it as an environment variable."
            )

        model = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini").strip()

        max_tokens = _parse_int("SUMMARIZER_MAX_TOKENS", default=1024, min_val=1, max_val=8192)
        timeout = _parse_int("SUMMARIZER_TIMEOUT", default=30, min_val=1, max_val=300)

        logger.debug(
            "Config loaded — model=%s, max_tokens=%d, timeout=%d",
            model,
            max_tokens,
            timeout,
        )

        return cls(api_key=api_key, model=model, max_tokens=max_tokens, timeout=timeout)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _parse_int(env_var: str, default: int, min_val: int, max_val: int) -> int:
    """Parse an integer environment variable with range validation."""
    raw = os.getenv(env_var, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(
            f"{env_var} must be an integer, got: {raw!r}"
        )
    if not (min_val <= value <= max_val):
        raise ConfigError(
            f"{env_var} must be between {min_val} and {max_val}, got: {value}"
        )
    return value


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""