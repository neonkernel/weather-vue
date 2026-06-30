"""Configuration management for the summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SummarizerConfig:
    """
    Central configuration object for the summarizer.

    Values are resolved from explicit constructor arguments first,
    then from environment variables, then from built-in defaults.
    """

    # ------------------------------------------------------------------
    # LLM provider selection
    # ------------------------------------------------------------------
    provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "openai"))
    """Which LLM backend to use: 'openai', 'anthropic', or 'ollama'."""

    # ------------------------------------------------------------------
    # Model selection (provider-specific defaults apply when None/empty)
    # ------------------------------------------------------------------
    model: Optional[str] = field(
        default_factory=lambda: os.environ.get("DEFAULT_MODEL") or None
    )
    """Override the provider's default model."""

    # ------------------------------------------------------------------
    # API keys
    # ------------------------------------------------------------------
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY") or None
    )
    """OpenAI API key (falls back to OPENAI_API_KEY env var)."""

    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY") or None
    )
    """Anthropic API key (falls back to ANTHROPIC_API_KEY env var)."""

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------
    ollama_host: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    )
    """Base URL of the local Ollama instance."""

    # ------------------------------------------------------------------
    # Generation parameters
    # ------------------------------------------------------------------
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("MAX_TOKENS", "4096"))
    )
    """Maximum tokens for LLM completions."""

    temperature: float = 0.3
    """Sampling temperature for generation."""

    # ------------------------------------------------------------------
    # Summarization behaviour
    # ------------------------------------------------------------------
    style: str = "concise"
    """Summary style: 'concise', 'detailed', 'bullet', etc."""

    chunk_size: int = 3000
    """Target chunk size in tokens for long-document processing."""

    chunk_overlap: int = 200
    """Token overlap between adjacent chunks."""

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "SummarizerConfig":
        """Create a config instance populated entirely from environment variables."""
        return cls()

    def validate(self) -> None:
        """
        Validate the configuration for the selected provider.

        Raises:
            ValueError: If required fields are missing for the chosen provider.
        """
        valid_providers = {"openai", "anthropic", "ollama"}
        if self.provider not in valid_providers:
            raise ValueError(
                f"Invalid provider '{self.provider}'. "
                f"Must be one of: {', '.join(sorted(valid_providers))}"
            )

        if self.provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "provider='openai' requires OPENAI_API_KEY to be set."
            )

        if self.provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "provider='anthropic' requires ANTHROPIC_API_KEY to be set."
            )

        if self.max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer.")

        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0.")