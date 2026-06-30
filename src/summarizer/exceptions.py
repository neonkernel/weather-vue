"""Shared exception hierarchy for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """Raised when an LLM provider call fails for any reason.

    This includes authentication errors, rate limits, network issues,
    malformed responses, and provider-specific errors.
    """


class IngestionError(SummarizerError):
    """Raised when input text cannot be fetched or parsed."""


class ConfigurationError(SummarizerError):
    """Raised when the summarizer is misconfigured."""