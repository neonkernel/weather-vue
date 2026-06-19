"""
Configuration management for the Summarizer CLI.

Loads and validates environment variables via python-dotenv and exposes
a Config dataclass with all necessary settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _find_dotenv() -> Path | None:
    """Walk up from cwd looking for a .env file."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    api_key: str = ""
    model: str = "gpt-4o-mini"
    max_tokens: int = 512
    log_level: str = "INFO"

    # Internal flag: True when the API key is present (even if not yet validated)
    _has_api_key: bool = field(init=False, repr=False, default=False)

    def __post_init__(self) -> None:
        self._has_api_key = bool(self.api_key)

    @property
    def has_api_key(self) -> bool:
        """Return True if an API key is configured."""
        return self._has_api_key

    def validate(self, require_api_key: bool = False) -> None:
        """
        Validate the configuration values.

        Args:
            require_api_key: When True, raise ConfigError if no API key is set.

        Raises:
            ConfigError: If any required value is missing or invalid.
        """
        if require_api_key and not self.api_key:
            raise ConfigError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or set it as an environment variable."
            )

        if self.max_tokens < 1:
            raise ConfigError(f"MAX_TOKENS must be a positive integer, got {self.max_tokens!r}.")

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ConfigError(
                f"LOG_LEVEL must be one of {sorted(valid_levels)}, got {self.log_level!r}."
            )


class ConfigError(Exception):
    """Raised when configuration is invalid or missing required values."""


def load_config(env_file: str | Path | None = None) -> Config:
    """
    Load configuration from environment variables, optionally from a .env file.

    The lookup order for each variable follows python-dotenv's standard:
    existing environment variables take precedence over .env file values.

    Args:
        env_file: Path to a .env file. If None, auto-discovers one by walking up
                  from the current working directory. Pass ``False`` to skip
                  .env loading entirely.

    Returns:
        A populated :class:`Config` instance.
    """
    if env_file is not False:
        dotenv_path = Path(env_file) if env_file else _find_dotenv()
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path, override=False)
        else:
            # Still attempt a default load so DOTENV_PATH etc. work
            load_dotenv(override=False)

    def _int(key: str, default: int) -> int:
        raw = os.getenv(key, "")
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"Environment variable {key} must be an integer, got {raw!r}.")

    return Config(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini"),
        max_tokens=_int("MAX_TOKENS", 512),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )