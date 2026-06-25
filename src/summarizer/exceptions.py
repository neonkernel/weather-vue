"""Custom exceptions for the summarizer."""


class SummarizationError(Exception):
    """Raised when summarization fails."""


class ConfigurationError(Exception):
    """Raised when the summarizer is misconfigured."""


class IngestionError(Exception):
    """Raised when article ingestion fails."""