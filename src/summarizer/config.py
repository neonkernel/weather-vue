"""
Configuration management for the Summarizer package.

Loads environment variables from a ``.env`` file (if present) and exposes
them as a typed :class:`Config` dataclass.  Call :func:`load_config` once at
startup; all other modules should import and use the returned object.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from summarizer.logger import get_logger

logger = get_logger(__name__)

# Supported values for style / format options
VALID_STYLES = ("paragraph", "bullet", "tldr")
VALID_FORMATS = ("plain", "markdown", "json")


@dataclass
class Config:
    """Validated application configuration."""

    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 512
    default_style: str = "paragraph"
    default_format: str = "plain"

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )
        if self.max_tokens < 1:
            raise ValueError("SUMMARIZER_MAX_TOKENS must be a positive integer.")
        if self.default_style not in VALID_STYLES:
            raise ValueError(
                f"SUMMARIZER_DEFAULT_STYLE must be one of {VALID_STYLES}; "
                f"got {self.default_style!r}."
            )
        if self.default_format not in VALID_FORMATS:
            raise ValueError(
                f"SUMMARIZER_DEFAULT_FORMAT must be one of {VALID_FORMATS}; "
                f"got {self.default_format!r}."
            )


def load_config(env_file: str = ".env") -> Config:
    """Load and validate configuration from environment / .env file.

    Args:
        env_file: Path to the dotenv file.  Defaults to ``.env`` in the
            current working directory.  Silently ignored when the file does
            not exist.

    Returns:
        A validated :class:`Config` instance.

    Raises:
        ValueError: When a required variable is missing or a value is invalid.
        TypeError: When a numeric variable cannot be parsed as an integer.
    """
    load_dotenv(dotenv_path=env_file, override=False)
    logger.debug("Environment variables loaded from %r", env_file)

    api_key = os.getenv("OPENAI_API_KEY", "")

    model = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini")

    raw_max_tokens = os.getenv("SUMMARIZER_MAX_TOKENS", "512")
    try:
        max_tokens = int(raw_max_tokens)
    except ValueError as exc:
        raise TypeError(
            f"SUMMARIZER_MAX_TOKENS must be an integer; got {raw_max_tokens!r}."
        ) from exc

    default_style = os.getenv("SUMMARIZER_DEFAULT_STYLE", "paragraph")
    default_format = os.getenv("SUMMARIZER_DEFAULT_FORMAT", "plain")

    config = Config(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        default_style=default_style,
        default_format=default_format,
    )
    logger.debug("Config loaded: model=%s, max_tokens=%d", config.model, config.max_tokens)
    return config