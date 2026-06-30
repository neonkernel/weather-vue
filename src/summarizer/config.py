"""Configuration management for the summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Holds all runtime configuration for the summarizer."""

    # --- LLM Provider ---
    provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "openai"))
    model: Optional[str] = field(default_factory=lambda: os.environ.get("DEFAULT_MODEL"))

    # --- OpenAI ---
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY")
    )

    # --- Anthropic ---
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY")
    )

    # --- Ollama ---
    ollama_host: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    )

    # --- Generation ---
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("MAX_TOKENS", "4096"))
    )
    temperature: float = 0.3
    chunk_size: int = 3000  # tokens per chunk
    chunk_overlap: int = 200  # overlap between chunks

    # --- Output ---
    style: str = "default"
    output_format: str = "text"

    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config instance populated entirely from environment variables."""
        return cls()

    def with_overrides(self, **kwargs: object) -> "Config":
        """Return a copy of this config with specific fields overridden."""
        import dataclasses
        return dataclasses.replace(self, **kwargs)  # type: ignore[arg-type]