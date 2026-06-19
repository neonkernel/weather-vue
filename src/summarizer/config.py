"""
Configuration management for the AI summarizer.

Loads environment variables (from .env if present) and exposes them
as a validated Config dataclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from summarizer.logger import get_logger

log = get_logger("config")

# Load .env from the current working directory (or any parent).
# This is a no-op when the variables are already set in the environment.
load_dotenv()

_VALID_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
}


@dataclass(frozen=True)
class Config:
    """Immutable configuration object built from environment variables."""

    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    temperature: float = 0.7

    # Extra metadata — not required by the user
    env_file_loaded: bool = field(default=False, compare=False, repr=False)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "Config":
        """
        Build a Config instance from environment variables.

        Raises:
            ValueError: If a required variable is missing or a value is invalid.
        """
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )

        model = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini").strip()
        log.debug("Using model: %s", model)

        raw_max_tokens = os.getenv("SUMMARIZER_MAX_TOKENS", "1024")
        try:
            max_tokens = int(raw_max_tokens)
            if max_tokens < 1:
                raise ValueError("max_tokens must be >= 1")
        except ValueError as exc:
            raise ValueError(
                f"SUMMARIZER_MAX_TOKENS must be a positive integer, got: {raw_max_tokens!r}"
            ) from exc

        raw_temperature = os.getenv("SUMMARIZER_TEMPERATURE", "0.7")
        try:
            temperature = float(raw_temperature)
            if not (0.0 <= temperature <= 2.0):
                raise ValueError("temperature must be between 0.0 and 2.0")
        except ValueError as exc:
            raise ValueError(
                f"SUMMARIZER_TEMPERATURE must be a float in [0.0, 2.0], got: {raw_temperature!r}"
            ) from exc

        return cls(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def masked_api_key(self) -> str:
        """Return the API key with all but the last 4 characters masked."""
        if len(self.api_key) <= 4:
            return "****"
        return "*" * (len(self.api_key) - 4) + self.api_key[-4:]