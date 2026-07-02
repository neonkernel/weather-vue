"""Custom exceptions for the summarizer."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class IngestionError(SummarizerError):
    """Raised when article ingestion fails."""


class LLMError(SummarizerError):
    """Raised when the LLM call fails."""


class ConfigError(SummarizerError):
    """Raised for configuration problems."""


class RateLimitError(SummarizerError):
    """Raised when a rate limit is exceeded."""


class CacheError(SummarizerError):
    """Raised for cache-related errors."""