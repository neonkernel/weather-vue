"""
Configuration management for the summarizer CLI.

Loads environment variables (from a .env file if present) and exposes
them as a validated :class:`Config` dataclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from summarizer.logger import get_logger

log = get_logger(__name__)

# Load .env from the current working directory (or any parent that has one)
load_dotenv(dotenv_path=Path(".env"), override=False)


@dataclass(frozen=True)
class Config:
    """Validated application configuration."""

    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 512
    request_timeout: int = 30

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_env(cls) -> "Config":
        """
        Build a :class:`Config` instance from environment variables.

        Raises:
            ValueError: If a required environment variable is missing or
                        if a numeric variable cannot be parsed.
        """
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Copy .env.example to .env and add your key, "
                "or export the variable in your shell."
            )

        model = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

        max_tokens = _parse_int("SUMMARIZER_MAX_TOKENS", default=512, min_val=1, max_val=32_768)
        request_timeout = _parse_int(
            "SUMMARIZER_REQUEST_TIMEOUT", default=30, min_val=1, max_val=300
        )

        config = cls(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            request_timeout=request_timeout,
        )
        log.debug(
            "Config loaded: model=%s max_tokens=%d timeout=%ds",
            config.model,
            config.max_tokens,
            config.request_timeout,
        )
        return config


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def _parse_int(
    env_var: str,
    *,
    default: int,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """
    Parse an integer environment variable with optional range validation.

    Args:
        env_var:   Name of the environment variable.
        default:   Fallback value when the variable is unset or empty.
        min_val:   Inclusive lower bound (optional).
        max_val:   Inclusive upper bound (optional).

    Returns:
        The parsed integer value.

    Raises:
        ValueError: If the value is not a valid integer or out of range.
    """
    raw = os.getenv(env_var, "").strip()
    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"Environment variable {env_var!r} must be an integer, got {raw!r}."
        ) from exc

    if min_val is not None and value < min_val:
        raise ValueError(
            f"Environment variable {env_var!r} must be >= {min_val}, got {value}."
        )
    if max_val is not None and value > max_val:
        raise ValueError(
            f"Environment variable {env_var!r} must be <= {max_val}, got {value}."
        )

    return value