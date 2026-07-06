"""
Custom exceptions for the summarizer package.
"""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""
    pass


class ConfigError(SummarizerError):
    """Raised for configuration errors (invalid values, missing files, etc.)."""
    pass


class ProfileNotFoundError(ConfigError):
    """Raised when a requested profile does not exist."""
    pass


class ValidationError(ConfigError):
    """Raised when config file fails schema validation."""
    pass


class ProviderError(SummarizerError):
    """Raised when an LLM provider encounters an error."""
    pass


class RateLimitError(SummarizerError):
    """Raised when rate limits are exceeded."""
    pass


class CacheError(SummarizerError):
    """Raised when cache operations fail."""
    pass


class IngestError(SummarizerError):
    """Raised when content ingestion fails."""
    pass