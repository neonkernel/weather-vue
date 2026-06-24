"""Custom exceptions for the summarizer."""

from __future__ import annotations


class SummarizerError(Exception):
    """Base exception for summarizer errors."""


class ConfigurationError(SummarizerError):
    """Raised when there is a configuration problem."""


class IngestionError(SummarizerError):
    """Raised when article ingestion fails."""


class LLMError(SummarizerError):
    """Raised when an LLM API call fails."""