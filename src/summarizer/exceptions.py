"""Custom exception hierarchy for the summariser."""


class SummarizerError(Exception):
    """Base exception for all summariser errors."""


class LLMError(SummarizerError):
    """Raised when an LLM provider encounters an error."""


class IngestionError(SummarizerError):
    """Raised when article ingestion fails."""


class ConfigurationError(SummarizerError):
    """Raised for invalid or missing configuration."""