"""Application configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Central configuration for the summarizer application."""

    # --- LLM provider ---
    provider: str = field(
        default_factory=lambda: os.environ.get("LLM_PROVIDER", "openai")
    )

    # --- Model settings ---
    model: Optional[str] = field(
        default_factory=lambda: os.environ.get("DEFAULT_MODEL", None)
    )
    temperature: float = field(
        default_factory=lambda: float(os.environ.get("TEMPERATURE", "0.3"))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("MAX_TOKENS", "4096"))
    )

    # --- Provider credentials / endpoints ---
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY")
    )
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY")
    )
    ollama_host: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    )

    # --- Output settings ---
    output_format: str = "markdown"
    max_length: Optional[int] = None
    style: str = "concise"

    # --- Chunking ---
    chunk_size: int = field(
        default_factory=lambda: int(os.environ.get("CHUNK_SIZE", "3000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.environ.get("CHUNK_OVERLAP", "200"))
    )

    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config instance populated from environment variables."""
        return cls()

    def resolve_model(self) -> str:
        """Return the model to use, falling back to the provider default."""
        if self.model:
            return self.model
        # Import lazily to avoid circular imports
        from src.summarizer.llm.factory import ProviderFactory  # noqa: F401
        _defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-20241022",
            "ollama": "llama3.2",
        }
        return _defaults.get(self.provider, "gpt-4o-mini")