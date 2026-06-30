"""Custom exceptions for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """Raised when an LLM provider call fails."""


class IngestionError(SummarizerError):
    """Raised when fetching or parsing input content fails."""


class ConfigError(SummarizerError):
    """Raised for invalid or missing configuration."""