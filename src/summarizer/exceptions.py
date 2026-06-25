"""Custom exceptions for the summarizer."""

from __future__ import annotations


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class IngestionError(SummarizerError):
    """Raised when article content cannot be fetched or parsed."""


class LLMError(SummarizerError):
    """Raised when the LLM API returns an unrecoverable error."""


class ConfigurationError(SummarizerError):
    """Raised for invalid configuration values."""