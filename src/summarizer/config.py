"""Configuration for the summarizer package."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Configuration for the summarizer.

    Attributes:
        openai_api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        model: Model to use for summarization.
        temperature: Sampling temperature (0.0 to 2.0).
        max_tokens: Maximum tokens in the response.
        base_url: Optional base URL for compatible endpoints.
        max_chunk_tokens: Maximum tokens per chunk for long articles.
        overlap_tokens: Token overlap between chunks.
    """

    openai_api_key: Optional[str] = field(
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
    base_url: Optional[str] = field(
        default_factory=lambda: os.environ.get("OPENAI_BASE_URL")
    )
    max_chunk_tokens: int = field(
        default_factory=lambda: int(os.environ.get("SUMMARIZER_MAX_CHUNK_TOKENS", "4000"))
    )
    overlap_tokens: int = field(
        default_factory=lambda: int(os.environ.get("SUMMARIZER_OVERLAP_TOKENS", "200"))
    )