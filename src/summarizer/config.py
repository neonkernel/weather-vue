"""Configuration for the summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Summarizer configuration.

    Attributes:
        openai_api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        model: Model to use for completions.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens for completion responses.
        max_retries: Number of retries for transient API errors.
        base_url: Optional custom base URL for compatible endpoints.
    """

    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY")
    )
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 1024
    max_retries: int = 3
    base_url: Optional[str] = None