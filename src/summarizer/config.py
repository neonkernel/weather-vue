"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """
    Central configuration object for the summarizer.

    Values can be set programmatically or loaded from environment variables
    via :meth:`from_env`.
    """

    # ---------------------------------------------------------------------------
    # Provider selection
    # ---------------------------------------------------------------------------
    provider: str = "openai"
    """Which LLM provider to use: 'openai', 'anthropic', or 'ollama'."""

    # ---------------------------------------------------------------------------
    # Model selection (provider-specific default applies when None)
    # ---------------------------------------------------------------------------
    model: str | None = None
    """Model name override. When None, the provider uses its own default."""

    # ---------------------------------------------------------------------------
    # OpenAI
    # ---------------------------------------------------------------------------
    openai_api_key: str | None = None
    """OpenAI API key. Falls back to OPENAI_API_KEY env var inside the provider."""

    # ---------------------------------------------------------------------------
    # Anthropic
    # ---------------------------------------------------------------------------
    anthropic_api_key: str | None = None
    """Anthropic API key. Falls back to ANTHROPIC_API_KEY env var inside the provider."""

    # ---------------------------------------------------------------------------
    # Ollama
    # ---------------------------------------------------------------------------
    ollama_host: str | None = None
    """Base URL for a local Ollama instance (e.g. http://localhost:11434)."""

    # ---------------------------------------------------------------------------
    # Summarization behaviour
    # ---------------------------------------------------------------------------
    max_chunk_tokens: int = 3000
    """Maximum tokens per chunk when splitting long documents."""

    temperature: float = 0.3
    """Sampling temperature passed to the LLM."""

    max_tokens: int = 1024
    """Maximum tokens in the LLM response."""

    style: str = "concise"
    """Summary style (e.g. 'concise', 'detailed', 'bullet')."""

    language: str = "en"
    """Output language for the summary."""

    # ---------------------------------------------------------------------------
    # Misc
    # ---------------------------------------------------------------------------
    verbose: bool = False
    """Enable verbose/debug logging."""

    extra: dict = field(default_factory=dict)
    """Arbitrary extra options for future extensibility."""

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "Config":
        """
        Build a :class:`Config` populated from environment variables.

        Environment variables recognised:
            LLM_PROVIDER        → provider
            LLM_MODEL           → model
            OPENAI_API_KEY      → openai_api_key
            ANTHROPIC_API_KEY   → anthropic_api_key
            OLLAMA_HOST         → ollama_host
            MAX_CHUNK_TOKENS    → max_chunk_tokens
            TEMPERATURE         → temperature
            MAX_TOKENS          → max_tokens
            SUMMARY_STYLE       → style
            SUMMARY_LANGUAGE    → language
        """
        return cls(
            provider=os.environ.get("LLM_PROVIDER", "openai"),
            model=os.environ.get("LLM_MODEL") or None,
            openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
            ollama_host=os.environ.get("OLLAMA_HOST") or None,
            max_chunk_tokens=int(os.environ.get("MAX_CHUNK_TOKENS", "3000")),
            temperature=float(os.environ.get("TEMPERATURE", "0.3")),
            max_tokens=int(os.environ.get("MAX_TOKENS", "1024")),
            style=os.environ.get("SUMMARY_STYLE", "concise"),
            language=os.environ.get("SUMMARY_LANGUAGE", "en"),
            verbose=os.environ.get("VERBOSE", "").lower() in ("1", "true", "yes"),
        )

    def merge_cli_args(self, **cli_kwargs: object) -> "Config":
        """
        Return a *new* Config with any non-None CLI keyword arguments applied.

        This allows CLI flags to override env-var / default values without
        mutating the original config.
        """
        import dataclasses
        current = dataclasses.asdict(self)
        for key, value in cli_kwargs.items():
            if value is not None and key in current:
                current[key] = value
        return Config(**current)