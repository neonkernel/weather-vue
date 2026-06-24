"""Custom exceptions for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class SummarizationError(SummarizerError):
    """Raised when summarization fails."""


class ConfigurationError(SummarizerError):
    """Raised when configuration is invalid or missing."""


class IngestionError(SummarizerError):
    """Raised when article ingestion fails."""


class TokenLimitError(SummarizerError):
    """Raised when token limits are exceeded."""