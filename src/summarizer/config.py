"""Configuration loading for the summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Summarizer configuration."""

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"
    default_style: str = "default"
    cache_dir: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.3


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        default_model=os.environ.get("SUMMARIZER_MODEL", "gpt-3.5-turbo"),
        default_style=os.environ.get("SUMMARIZER_STYLE", "default"),
        cache_dir=os.environ.get("SUMMARIZER_CACHE_DIR"),
        max_tokens=int(os.environ.get("SUMMARIZER_MAX_TOKENS", "1024")),
        temperature=float(os.environ.get("SUMMARIZER_TEMPERATURE", "0.3")),
    )