"""Configuration dataclass for the summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

ProviderName = Literal["openai", "anthropic", "ollama"]


@dataclass
class SummarizerConfig:
    """Holds all runtime configuration for the summarizer.

    Values are resolved from (in priority order):
    1. Explicit constructor arguments
    2. Environment variables
    3. Hard-coded defaults
    """

    # --- Provider selection ---
    provider: ProviderName = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai")  # type: ignore[return-value]
    )

    # --- OpenAI ---
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    default_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL", "")
    )

    # --- Anthropic ---
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )

    # --- Ollama ---
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )

    # --- General LLM parameters ---
    temperature: float = field(
        default_factory=lambda: float(os.getenv("TEMPERATURE", "0.3"))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_TOKENS", "4096"))
    )

    # --- Summarization behaviour ---
    style: str = field(
        default_factory=lambda: os.getenv("SUMMARY_STYLE", "concise")
    )
    language: str = field(
        default_factory=lambda: os.getenv("SUMMARY_LANGUAGE", "en")
    )
    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "3000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200"))
    )

    # --- Output ---
    output_format: str = field(
        default_factory=lambda: os.getenv("OUTPUT_FORMAT", "text")
    )
    verbose: bool = field(
        default_factory=lambda: os.getenv("VERBOSE", "").lower() in ("1", "true", "yes")
    )

    @classmethod
    def from_env(cls) -> "SummarizerConfig":
        """Create a config instance populated entirely from environment variables."""
        return cls()

    def validate(self) -> None:
        """Raise ValueError if the config is in an invalid state."""
        valid_providers = ("openai", "anthropic", "ollama")
        if self.provider not in valid_providers:
            raise ValueError(
                f"Invalid provider '{self.provider}'. "
                f"Must be one of: {', '.join(valid_providers)}"
            )

        if self.provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "openai_api_key is required when provider is 'openai'. "
                "Set the OPENAI_API_KEY environment variable."
            )

        if self.provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "anthropic_api_key is required when provider is 'anthropic'. "
                "Set the ANTHROPIC_API_KEY environment variable."
            )

        if self.temperature < 0.0 or self.temperature > 2.0:
            raise ValueError(
                f"temperature must be between 0.0 and 2.0, got {self.temperature}"
            )

        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be >= 1, got {self.max_tokens}")