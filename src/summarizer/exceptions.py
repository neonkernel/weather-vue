"""Custom exceptions for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for summarizer errors."""


class FetchError(SummarizerError):
    """Raised when fetching an article fails."""


class ParseError(SummarizerError):
    """Raised when parsing article content fails."""


class LLMError(SummarizerError):
    """Raised when the LLM API call fails."""


class ConfigError(SummarizerError):
    """Raised for configuration errors."""


class RateLimitError(LLMError):
    """Raised when the LLM rate limit is exceeded."""


class BatchError(SummarizerError):
    """Raised for batch processing errors."""