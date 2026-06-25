"""Configuration management for the summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Runtime configuration, populated from environment variables or explicit values."""

    openai_api_key: str | None = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY")
    )
    model: str = field(
        default_factory=lambda: os.environ.get("SUMMARIZER_MODEL", "gpt-4o-mini")
    )
    temperature: float = field(
        default_factory=lambda: float(os.environ.get("SUMMARIZER_TEMPERATURE", "0.3"))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("SUMMARIZER_MAX_TOKENS", "1024"))
    )
    chunk_size: int = field(
        default_factory=lambda: int(os.environ.get("SUMMARIZER_CHUNK_SIZE", "3000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.environ.get("SUMMARIZER_CHUNK_OVERLAP", "200"))
    )