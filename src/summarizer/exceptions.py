"""Shared exception types for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """
    Raised when an LLM provider encounters an error.

    This is the single exception type that all providers map their
    provider-specific errors to, so callers only need to catch one type.
    """


class IngestionError(SummarizerError):
    """Raised when content cannot be fetched or parsed."""


class ConfigError(SummarizerError):
    """Raised for invalid or missing configuration."""


class ChunkingError(SummarizerError):
    """Raised when text chunking fails."""