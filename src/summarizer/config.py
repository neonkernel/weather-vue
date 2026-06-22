"""
Configuration management for the summarizer package.

Loads and validates environment variables via python-dotenv and exposes
them through a frozen Config dataclass so the rest of the application
treats configuration as immutable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from summarizer.logger import get_logger

logger = get_logger(__name__)

# Default values
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_MAX_TOKENS = 512
_DEFAULT_TEMPERATURE = 0.3


@dataclass(frozen=True)
class Config:
    """
    Immutable configuration object populated from environment variables.

    Attributes:
        api_key:     OpenAI API key (required for summarization).
        model:       Model identifier to use (e.g. 'gpt-4o-mini').
        max_tokens:  Maximum number of tokens in the model response.
        temperature: Sampling temperature passed to the model.
    """

    api_key: Optional[str]
    model: str
    max_tokens: int
    temperature: float

    def is_api_key_set(self) -> bool:
        """Return True if an API key has been configured."""
        return bool(self.api_key and self.api_key.strip())


def load_config(env_file: Optional[str | Path] = None) -> Config:
    """
    Load configuration from environment variables (and an optional .env file).

    Resolution order (highest priority first):
        1. Existing environment variables (set before the process started)
        2. Variables defined in *env_file* (defaults to '.env' in the CWD)

    Args:
        env_file: Path to a .env file. Pass ``None`` to use the default
                  discovery logic of python-dotenv (looks for '.env' in
                  the current directory and its parents).

    Returns:
        A fully populated :class:`Config` instance.

    Raises:
        ValueError: If any value fails type coercion (e.g. a non-numeric
                    MAX_TOKENS).
    """
    # Load .env — override=False means real env vars take precedence
    if env_file is not None:
        load_dotenv(dotenv_path=env_file, override=False)
        logger.debug("Loaded environment from %s", env_file)
    else:
        load_dotenv(override=False)
        logger.debug("Loaded environment from default .env discovery")

    api_key = os.getenv("OPENAI_API_KEY") or None

    model = os.getenv("SUMMARIZER_MODEL", _DEFAULT_MODEL).strip()

    raw_max_tokens = os.getenv("SUMMARIZER_MAX_TOKENS", str(_DEFAULT_MAX_TOKENS))
    try:
        max_tokens = int(raw_max_tokens)
        if max_tokens <= 0:
            raise ValueError("must be positive")
    except ValueError as exc:
        raise ValueError(
            f"Invalid SUMMARIZER_MAX_TOKENS={raw_max_tokens!r}: {exc}"
        ) from exc

    raw_temperature = os.getenv("SUMMARIZER_TEMPERATURE", str(_DEFAULT_TEMPERATURE))
    try:
        temperature = float(raw_temperature)
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("must be between 0.0 and 2.0")
    except ValueError as exc:
        raise ValueError(
            f"Invalid SUMMARIZER_TEMPERATURE={raw_temperature!r}: {exc}"
        ) from exc

    config = Config(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    logger.debug(
        "Config loaded: model=%s, max_tokens=%d, temperature=%.2f, api_key_set=%s",
        config.model,
        config.max_tokens,
        config.temperature,
        config.is_api_key_set(),
    )

    return config