"""Custom exceptions for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """
    Raised when an LLM provider encounters an error.

    This includes authentication failures, rate limits, network errors,
    invalid responses, and model-not-found errors.
    """


class IngestionError(SummarizerError):
    """Raised when document ingestion or parsing fails."""


class ConfigurationError(SummarizerError):
    """Raised when the configuration is invalid or incomplete."""


class ChunkingError(SummarizerError):
    """Raised when document chunking fails."""