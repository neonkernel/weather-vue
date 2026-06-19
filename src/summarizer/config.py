"""
Configuration management for the summarizer package.

Loads environment variables from a .env file (if present) via python-dotenv
and exposes a validated Config dataclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from summarizer.logger import get_logger

logger = get_logger("config")

# Load .env from the current working directory (or project root).
# Does NOT override existing environment variables.
load_dotenv(override=False)


@dataclass
class Config:
    """
    Holds validated runtime configuration values.

    All values are sourced from environment variables (with defaults where
    applicable).  Raises ValueError on construction if required values are
    missing or invalid.
    """

    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    timeout: int = 30
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        """Validate field values after dataclass initialisation."""
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Please add it to your .env file or export it as an environment variable."
            )

        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(
                f"Invalid SUMMARIZER_LOG_LEVEL '{self.log_level}'. "
                f"Must be one of: {', '.join(sorted(valid_log_levels))}"
            )

        if self.max_tokens < 1:
            raise ValueError(
                f"SUMMARIZER_MAX_TOKENS must be a positive integer, got {self.max_tokens}."
            )

        if self.timeout < 1:
            raise ValueError(
                f"SUMMARIZER_TIMEOUT must be a positive integer, got {self.timeout}."
            )


def _get_int_env(key: str, default: int) -> int:
    """Parse an integer environment variable, falling back to *default*."""
    raw = os.getenv(key, "")
    if not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        logger.warning(
            "Environment variable %s='%s' is not a valid integer; using default %d.",
            key,
            raw,
            default,
        )
        return default


def load_config() -> Config:
    """
    Build and return a Config instance from environment variables.

    Returns:
        A validated Config dataclass.

    Raises:
        ValueError: If required variables are missing or invalid.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini")
    max_tokens = _get_int_env("SUMMARIZER_MAX_TOKENS", 1024)
    timeout = _get_int_env("SUMMARIZER_TIMEOUT", 30)
    log_level = os.getenv("SUMMARIZER_LOG_LEVEL", "INFO")

    config = Config(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
        log_level=log_level.upper(),
    )

    logger.debug(
        "Config loaded: model=%s, max_tokens=%d, timeout=%d, log_level=%s",
        config.model,
        config.max_tokens,
        config.timeout,
        config.log_level,
    )

    return config