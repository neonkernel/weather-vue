"""Application configuration: reads from environment variables and CLI overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Centralised configuration for the summariser."""

    # --- Provider selection ---
    provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai")
    )

    # --- Model ---
    model: Optional[str] = field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL", "")
    )

    # --- OpenAI ---
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # --- Anthropic ---
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )

    # --- Ollama ---
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )

    # --- Generation parameters ---
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_TOKENS", "4096"))
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv("TEMPERATURE", "0.3"))
    )

    # --- Chunking ---
    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "3000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200"))
    )

    # --- Output ---
    style: str = field(
        default_factory=lambda: os.getenv("SUMMARY_STYLE", "concise")
    )
    output_format: str = field(
        default_factory=lambda: os.getenv("OUTPUT_FORMAT", "text")
    )

    def __post_init__(self) -> None:
        # Normalise empty strings to None for optional secrets
        if not self.openai_api_key:
            self.openai_api_key = None
        if not self.anthropic_api_key:
            self.anthropic_api_key = None
        if not self.model:
            self.model = None

    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config instance populated purely from environment variables."""
        return cls()

    def with_overrides(self, **overrides: object) -> "Config":
        """Return a *new* Config with the supplied keyword arguments overriding defaults."""
        import dataclasses

        current = dataclasses.asdict(self)
        current.update({k: v for k, v in overrides.items() if v is not None})
        return Config(**current)