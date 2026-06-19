"""
Configuration management for the Summarizer CLI.

Loads and validates environment variables via python-dotenv and exposes
them through a typed Config dataclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the current working directory (or any parent) automatically.
# This is a no-op if no .env file is found.
load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass
class Config:
    """
    Application configuration loaded from environment variables.

    All fields have sensible defaults except `api_key`, which must be
    provided when LLM features are used (Phase 2+).
    """

    api_key: str = field(default="")
    model: str = field(default="gpt-4o-mini")
    max_tokens: int = field(default=512)
    temperature: float = field(default=0.3)

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_env(cls) -> "Config":
        """
        Build a Config instance from environment variables.

        Environment variables
        --------------------
        OPENAI_API_KEY        — OpenAI API key (required for LLM calls)
        SUMMARIZER_MODEL      — model identifier (default: gpt-4o-mini)
        SUMMARIZER_MAX_TOKENS — max tokens in summary (default: 512)
        SUMMARIZER_TEMPERATURE — sampling temperature (default: 0.3)
        """
        api_key = os.getenv("OPENAI_API_KEY", "")

        model = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini")

        raw_max_tokens = os.getenv("SUMMARIZER_MAX_TOKENS", "512")
        try:
            max_tokens = int(raw_max_tokens)
            if max_tokens < 1:
                raise ValueError("must be a positive integer")
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid SUMMARIZER_MAX_TOKENS={raw_max_tokens!r}: {exc}"
            ) from exc

        raw_temperature = os.getenv("SUMMARIZER_TEMPERATURE", "0.3")
        try:
            temperature = float(raw_temperature)
            if not (0.0 <= temperature <= 2.0):
                raise ValueError("must be between 0.0 and 2.0")
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid SUMMARIZER_TEMPERATURE={raw_temperature!r}: {exc}"
            ) from exc

        return cls(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # ------------------------------------------------------------------ #
    # Validation helpers                                                   #
    # ------------------------------------------------------------------ #

    def require_api_key(self) -> None:
        """
        Assert that an API key is present.

        Call this before making any LLM requests (Phase 2+).

        Raises
        ------
        ConfigurationError
            If OPENAI_API_KEY is not set or is empty.
        """
        if not self.api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )