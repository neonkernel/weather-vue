"""Shared exception hierarchy for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """Raised when an LLM provider encounters an error."""


class IngestionError(SummarizerError):
    """Raised when content ingestion (fetch/parse) fails."""


class ConfigError(SummarizerError):
    """Raised for invalid or missing configuration."""