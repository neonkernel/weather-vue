"""Configuration management for the summarizer package."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Application configuration.

    Values are read from environment variables with sensible defaults.
    """

    openai_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    openai_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
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