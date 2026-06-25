"""Exceptions for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for summarizer errors."""
    pass


class IngestionError(SummarizerError):
    """Raised when article ingestion fails."""
    pass


class LLMError(SummarizerError):
    """Raised when an LLM API call fails."""
    pass


class ConfigurationError(SummarizerError):
    """Raised when configuration is invalid."""
    pass