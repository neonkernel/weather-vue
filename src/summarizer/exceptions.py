"""
Shared exception base classes for the summarizer package.
"""
from __future__ import annotations


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""
    pass


class IngestionError(SummarizerError):
    """Raised when content ingestion fails."""
    pass


class LLMError(SummarizerError):
    """Raised when an LLM call fails."""
    pass


class RateLimitError(SummarizerError):
    """Raised when a rate limit is exceeded."""
    pass


class CacheError(SummarizerError):
    """Raised when a cache operation fails."""
    pass