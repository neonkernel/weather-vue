"""Custom exceptions for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """Raised when an LLM provider encounters an error."""


class IngestionError(SummarizerError):
    """Raised when document ingestion fails."""


class ConfigError(SummarizerError):
    """Raised when configuration is invalid."""