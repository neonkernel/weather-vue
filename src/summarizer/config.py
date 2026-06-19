"""
Configuration management for the Summarizer CLI.

Loads environment variables (from a .env file or the shell environment)
and exposes them through a validated Config dataclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from summarizer.logger import get_logger

logger = get_logger("config")

# Load .env from the project root (or wherever the process is run from).
# Variables already present in the environment take precedence.
_ENV_FILE = Path(".env")


def _load_env(env_file: Path = _ENV_FILE) -> None:
    """Load environment variables from a .env file if it exists."""
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)
        logger.debug("Loaded environment variables from: %s", env_file.resolve())
    else:
        logger.debug(".env file not found at %s; relying on shell environment.", env_file)


@dataclass(frozen=True)
class Config:
    """
    Immutable configuration object populated from environment variables.

    Attributes:
        api_key:    OpenAI API key (required for summarization).
        model:      OpenAI model identifier.
        max_tokens: Maximum number of tokens in the model response.
        timeout:    HTTP request timeout in seconds.
    """

    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 512
    timeout: int = 30

    # Internal sentinel: tracks whether the config was loaded successfully
    _loaded: bool = field(default=True, compare=False, repr=False)

    def is_api_key_set(self) -> bool:
        """Return True if the API key looks like a real key (not the placeholder)."""
        return bool(self.api_key) and not self.api_key.startswith("sk-...")


class ConfigError(Exception):
    """Raised when required configuration values are missing or invalid."""


def load_config(env_file: Path = _ENV_FILE) -> Config:
    """
    Load and validate configuration from environment variables.

    Reads from the given .env file (if it exists) and then from the
    process environment.  Raises ConfigError if required values are
    absent or invalid.

    Args:
        env_file: Path to the .env file to load.

    Returns:
        A populated and validated Config instance.

    Raises:
        ConfigError: If OPENAI_API_KEY is missing.
    """
    _load_env(env_file)

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file or export it in your shell.\n"
            "  Example: export OPENAI_API_KEY=sk-..."
        )

    model = os.environ.get("SUMMARIZER_MODEL", "gpt-4o-mini").strip()
    if not model:
        model = "gpt-4o-mini"

    try:
        max_tokens = int(os.environ.get("SUMMARIZER_MAX_TOKENS", "512"))
        if max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")
    except ValueError as exc:
        raise ConfigError(
            f"SUMMARIZER_MAX_TOKENS must be a positive integer. Got: "
            f"{os.environ.get('SUMMARIZER_MAX_TOKENS')!r}"
        ) from exc

    try:
        timeout = int(os.environ.get("SUMMARIZER_TIMEOUT", "30"))
        if timeout < 1:
            raise ValueError("timeout must be a positive integer")
    except ValueError as exc:
        raise ConfigError(
            f"SUMMARIZER_TIMEOUT must be a positive integer. Got: "
            f"{os.environ.get('SUMMARIZER_TIMEOUT')!r}"
        ) from exc

    config = Config(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    logger.debug(
        "Config loaded: model=%s, max_tokens=%d, timeout=%d",
        config.model,
        config.max_tokens,
        config.timeout,
    )
    return config