"""Configuration management for the summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SummarizerConfig:
    """
    Central configuration object for the summarizer.

    Values are sourced (in priority order) from:
    1. Explicit constructor arguments
    2. Environment variables
    3. Defaults defined here
    """

    # ── Provider selection ────────────────────────────────────────────────────
    provider: str = field(
        default_factory=lambda: os.environ.get("LLM_PROVIDER", "openai")
    )

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    openai_model: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_MODEL") or None
    )

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    anthropic_model: Optional[str] = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_MODEL") or None
    )

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_host: str = field(
        default_factory=lambda: os.environ.get(
            "OLLAMA_HOST", "http://localhost:11434"
        )
    )
    ollama_model: Optional[str] = field(
        default_factory=lambda: os.environ.get("OLLAMA_MODEL") or None
    )

    # ── General summarizer settings ───────────────────────────────────────────
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("MAX_TOKENS", "4096"))
    )
    temperature: float = field(
        default_factory=lambda: float(os.environ.get("TEMPERATURE", "0.3"))
    )
    chunk_size: int = field(
        default_factory=lambda: int(os.environ.get("CHUNK_SIZE", "3000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.environ.get("CHUNK_OVERLAP", "200"))
    )

    @classmethod
    def from_env(cls) -> "SummarizerConfig":
        """Create a config instance populated entirely from environment variables."""
        return cls()

    def validate(self) -> None:
        """
        Validate that the configuration is consistent.

        Raises:
            ValueError: If required fields for the chosen provider are missing.
        """
        provider = self.provider.lower()

        if provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "OpenAI provider selected but OPENAI_API_KEY is not set."
            )

        if provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "Anthropic provider selected but ANTHROPIC_API_KEY is not set."
            )

        if provider not in ("openai", "anthropic", "ollama"):
            raise ValueError(
                f"Unknown provider '{provider}'. "
                "Valid options: openai, anthropic, ollama"
            )