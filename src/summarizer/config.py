"""
Configuration management for the Summarizer CLI.

Loads environment variables from a .env file (via python-dotenv) and exposes
them through a validated :class:`Config` dataclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from summarizer.logger import get_logger

log = get_logger("config")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_MAX_TOKENS = 512
_DEFAULT_TEMPERATURE = 0.3
_DEFAULT_REQUEST_TIMEOUT = 30


@dataclass
class Config:
    """
    Application configuration derived from environment variables.

    Attributes:
        api_key: OpenAI API key (required for LLM calls).
        model: OpenAI model name to use for summarization.
        max_tokens: Maximum tokens to generate per summary.
        temperature: Sampling temperature for the model.
        request_timeout: Timeout (seconds) for outbound HTTP requests.
    """

    api_key: str
    model: str = _DEFAULT_MODEL
    max_tokens: int = _DEFAULT_MAX_TOKENS
    temperature: float = _DEFAULT_TEMPERATURE
    request_timeout: int = _DEFAULT_REQUEST_TIMEOUT

    # Derived / private — not part of the public interface yet
    _raw: dict = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate field values after construction."""
        if not self.api_key:
            raise ConfigError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )
        if self.max_tokens < 1:
            raise ConfigError("SUMMARIZER_MAX_TOKENS must be a positive integer.")
        if not (0.0 <= self.temperature <= 2.0):
            raise ConfigError("SUMMARIZER_TEMPERATURE must be between 0.0 and 2.0.")
        if self.request_timeout < 1:
            raise ConfigError("SUMMARIZER_REQUEST_TIMEOUT must be a positive integer.")

        log.debug(
            "Config loaded: model=%s max_tokens=%d temperature=%.2f timeout=%ds",
            self.model,
            self.max_tokens,
            self.temperature,
            self.request_timeout,
        )


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def load_config(env_file: str | os.PathLike | None = None) -> Config:
    """
    Load configuration from environment variables, optionally reading a .env file.

    Resolution order (highest priority first):
    1. Already-set environment variables in the process.
    2. Variables defined in ``env_file`` (or ``.env`` in the current directory).

    Args:
        env_file: Path to a .env file. If *None*, python-dotenv searches for
                  ``.env`` starting from the current working directory.

    Returns:
        A populated and validated :class:`Config` instance.

    Raises:
        ConfigError: If required variables are missing or values are invalid.
    """
    _load_dotenv(env_file)

    raw: dict = {}

    api_key = os.getenv("OPENAI_API_KEY", "")

    model = os.getenv("SUMMARIZER_MODEL", _DEFAULT_MODEL).strip()

    try:
        max_tokens = int(os.getenv("SUMMARIZER_MAX_TOKENS", str(_DEFAULT_MAX_TOKENS)))
    except ValueError as exc:
        raise ConfigError(
            f"SUMMARIZER_MAX_TOKENS must be an integer, got: "
            f"{os.getenv('SUMMARIZER_MAX_TOKENS')!r}"
        ) from exc

    try:
        temperature = float(
            os.getenv("SUMMARIZER_TEMPERATURE", str(_DEFAULT_TEMPERATURE))
        )
    except ValueError as exc:
        raise ConfigError(
            f"SUMMARIZER_TEMPERATURE must be a float, got: "
            f"{os.getenv('SUMMARIZER_TEMPERATURE')!r}"
        ) from exc

    try:
        request_timeout = int(
            os.getenv("SUMMARIZER_REQUEST_TIMEOUT", str(_DEFAULT_REQUEST_TIMEOUT))
        )
    except ValueError as exc:
        raise ConfigError(
            f"SUMMARIZER_REQUEST_TIMEOUT must be an integer, got: "
            f"{os.getenv('SUMMARIZER_REQUEST_TIMEOUT')!r}"
        ) from exc

    return Config(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        request_timeout=request_timeout,
        _raw=raw,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_dotenv(env_file: str | os.PathLike | None) -> None:
    """Load a .env file without overriding existing environment variables."""
    if env_file is not None:
        dotenv_path = Path(env_file)
        if not dotenv_path.exists():
            log.warning(".env file not found at %s — skipping", dotenv_path)
            return
        load_dotenv(dotenv_path=dotenv_path, override=False)
        log.debug("Loaded .env from %s", dotenv_path)
    else:
        loaded = load_dotenv(override=False)
        if loaded:
            log.debug("Loaded .env from current/parent directory")
        else:
            log.debug("No .env file found; relying on shell environment")