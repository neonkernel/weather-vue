"""Custom exceptions for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """
    Raised when an LLM provider encounters an error.

    This covers authentication failures, rate limits, connection issues,
    and any other provider-level problems.
    """


class IngestionError(SummarizerError):
    """Raised when document ingestion (fetch / parse) fails."""


class ConfigurationError(SummarizerError):
    """Raised for invalid or missing configuration."""


class ChunkingError(SummarizerError):
    """Raised when text chunking fails."""