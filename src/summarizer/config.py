"""Configuration for the summarizer."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SummarizerConfig:
    """
    Configuration dataclass for the summarizer.

    All fields have sensible defaults and can be overridden via
    environment variables or direct instantiation.
    """

    # Model selection
    model: str = field(
        default_factory=lambda: os.environ.get("SUMMARIZER_MODEL", "gpt-4o-mini")
    )

    # API authentication
    api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY")
    )
    base_url: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_BASE_URL")
    )

    # Generation parameters
    temperature: float = field(
        default_factory=lambda: float(os.environ.get("SUMMARIZER_TEMPERATURE", "0.3"))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("SUMMARIZER_MAX_TOKENS", "1024"))
    )

    # Chunking parameters
    chunk_tokens: int = field(
        default_factory=lambda: int(os.environ.get("SUMMARIZER_CHUNK_TOKENS", "3000"))
    )
    overlap_tokens: int = field(
        default_factory=lambda: int(os.environ.get("SUMMARIZER_OVERLAP_TOKENS", "200"))
    )