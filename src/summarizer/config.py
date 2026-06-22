"""Configuration management for the Summarizer CLI.

Loads and validates environment variables via python-dotenv.
Exposes a Config dataclass with all runtime configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the current working directory or any parent directory
load_dotenv()


VALID_STYLES = ("brief", "detailed", "bullet")
VALID_FORMATS = ("text", "markdown", "json")


@dataclass
class Config:
    """Runtime configuration loaded from environment variables."""

    api_key: str = field(default="")
    model: str = field(default="gpt-4o-mini")
    max_tokens: int = field(default=512)
    default_style: str = field(default="brief")
    default_format: str = field(default="text")

    def __post_init__(self) -> None:
        if self.default_style not in VALID_STYLES:
            raise ValueError(
                f"Invalid SUMMARIZER_DEFAULT_STYLE '{self.default_style}'. "
                f"Must be one of: {', '.join(VALID_STYLES)}"
            )
        if self.default_format not in VALID_FORMATS:
            raise ValueError(
                f"Invalid SUMMARIZER_DEFAULT_FORMAT '{self.default_format}'. "
                f"Must be one of: {', '.join(VALID_FORMATS)}"
            )
        if self.max_tokens < 1:
            raise ValueError(
                f"SUMMARIZER_MAX_TOKENS must be a positive integer, got {self.max_tokens}"
            )

    @property
    def has_api_key(self) -> bool:
        """Return True if an API key has been configured."""
        return bool(self.api_key and self.api_key.strip())


def load_config() -> Config:
    """Load configuration from environment variables.

    Returns:
        A populated Config dataclass instance.

    Raises:
        ValueError: If any environment variable has an invalid value.
    """
    raw_max_tokens = os.getenv("SUMMARIZER_MAX_TOKENS", "512")
    try:
        max_tokens = int(raw_max_tokens)
    except ValueError:
        raise ValueError(
            f"SUMMARIZER_MAX_TOKENS must be an integer, got '{raw_max_tokens}'"
        )

    return Config(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini"),
        max_tokens=max_tokens,
        default_style=os.getenv("SUMMARIZER_DEFAULT_STYLE", "brief"),
        default_format=os.getenv("SUMMARIZER_DEFAULT_FORMAT", "text"),
    )