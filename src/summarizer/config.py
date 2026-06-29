"""Configuration management for the summarizer."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """
    Central configuration for the summarizer application.

    Values are resolved in this order (highest priority first):
    1. Explicit constructor arguments
    2. Environment variables
    3. Hard-coded defaults
    """

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------
    provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "openai"))

    # ------------------------------------------------------------------
    # OpenAI settings
    # ------------------------------------------------------------------
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY")
    )
    openai_model: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    )

    # ------------------------------------------------------------------
    # Anthropic settings
    # ------------------------------------------------------------------
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY")
    )
    anthropic_model: Optional[str] = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
    )

    # ------------------------------------------------------------------
    # Ollama settings
    # ------------------------------------------------------------------
    ollama_host: Optional[str] = field(
        default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    )
    ollama_model: Optional[str] = field(
        default_factory=lambda: os.environ.get("OLLAMA_MODEL", "llama3.2")
    )

    # ------------------------------------------------------------------
    # General summarizer settings
    # ------------------------------------------------------------------
    max_chunk_tokens: int = field(
        default_factory=lambda: int(os.environ.get("MAX_CHUNK_TOKENS", "3000"))
    )
    max_output_tokens: int = field(
        default_factory=lambda: int(os.environ.get("MAX_OUTPUT_TOKENS", "1024"))
    )
    temperature: float = field(
        default_factory=lambda: float(os.environ.get("TEMPERATURE", "0.3"))
    )
    style: str = field(
        default_factory=lambda: os.environ.get("SUMMARY_STYLE", "concise")
    )
    language: str = field(
        default_factory=lambda: os.environ.get("SUMMARY_LANGUAGE", "en")
    )

    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config instance populated entirely from environment variables."""
        return cls()

    def __post_init__(self) -> None:
        """Normalize values after initialization."""
        if self.provider:
            self.provider = self.provider.lower().strip()
        if self.ollama_host:
            self.ollama_host = self.ollama_host.rstrip("/")