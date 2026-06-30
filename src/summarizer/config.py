"""Application configuration, loaded from environment variables and CLI overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Centralised configuration for the summarizer application.

    Values are resolved in the following order (highest priority first):
    1. Explicit keyword arguments passed to :func:`from_env`.
    2. Environment variables.
    3. Hard-coded defaults.
    """

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------
    provider: str = "openai"
    """Which LLM backend to use: 'openai', 'anthropic', or 'ollama'."""

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------
    openai_api_key: str = ""
    model: Optional[str] = None
    """Overrides the provider's default model when set."""

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------
    anthropic_api_key: str = ""

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------
    ollama_host: str = "http://localhost:11434"

    # ------------------------------------------------------------------
    # Shared generation parameters
    # ------------------------------------------------------------------
    max_tokens: int = 4096
    temperature: float = 0.3

    # ------------------------------------------------------------------
    # Summarisation behaviour
    # ------------------------------------------------------------------
    style: str = "paragraph"
    max_length: int = 500
    chunk_size: int = 3000
    chunk_overlap: int = 200

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    verbose: bool = False
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, **overrides: object) -> "Config":
        """Create a :class:`Config` from environment variables.

        Any keyword argument supplied via *overrides* takes precedence over
        the corresponding environment variable.
        """

        def _get(key: str, default: object = None) -> object:
            """Return override > env var > default."""
            if key in overrides:
                return overrides[key]
            return os.environ.get(key.upper(), default)

        provider = str(_get("provider", os.environ.get("LLM_PROVIDER", "openai")))

        openai_api_key = str(_get("openai_api_key", os.environ.get("OPENAI_API_KEY", "")))
        anthropic_api_key = str(
            _get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
        )
        ollama_host = str(
            _get("ollama_host", os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
        )

        model_val = _get("model", os.environ.get("DEFAULT_MODEL"))
        model: Optional[str] = str(model_val) if model_val else None

        max_tokens_raw = _get("max_tokens", os.environ.get("MAX_TOKENS", 4096))
        max_tokens = int(max_tokens_raw)  # type: ignore[arg-type]

        temperature_raw = _get("temperature", os.environ.get("TEMPERATURE", 0.3))
        temperature = float(temperature_raw)  # type: ignore[arg-type]

        style = str(_get("style", os.environ.get("SUMMARY_STYLE", "paragraph")))
        max_length_raw = _get("max_length", os.environ.get("MAX_LENGTH", 500))
        max_length = int(max_length_raw)  # type: ignore[arg-type]

        chunk_size_raw = _get("chunk_size", os.environ.get("CHUNK_SIZE", 3000))
        chunk_size = int(chunk_size_raw)  # type: ignore[arg-type]

        chunk_overlap_raw = _get("chunk_overlap", os.environ.get("CHUNK_OVERLAP", 200))
        chunk_overlap = int(chunk_overlap_raw)  # type: ignore[arg-type]

        verbose_raw = _get("verbose", os.environ.get("VERBOSE", False))
        if isinstance(verbose_raw, str):
            verbose = verbose_raw.lower() in ("1", "true", "yes")
        else:
            verbose = bool(verbose_raw)

        return cls(
            provider=provider,
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key,
            ollama_host=ollama_host,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            style=style,
            max_length=max_length,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            verbose=verbose,
        )