"""Custom exception hierarchy for the summarizer."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""

    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause

    def __str__(self):
        base = super().__str__()
        if self.cause:
            return f"{base} (caused by: {type(self.cause).__name__}: {self.cause})"
        return base


class FetchError(SummarizerError):
    """Raised when an article cannot be fetched from a URL or file system."""

    def __init__(self, message: str, url: str = None, cause: Exception = None):
        super().__init__(message, cause=cause)
        self.url = url

    def __str__(self):
        base = super().__str__()
        if self.url:
            return f"{base} [url={self.url}]"
        return base


class ParseError(SummarizerError):
    """Raised when article content cannot be parsed or extracted."""

    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message, cause=cause)


class LLMError(SummarizerError):
    """Raised when the LLM API call fails or returns an unexpected result."""

    def __init__(self, message: str, model: str = None, cause: Exception = None):
        super().__init__(message, cause=cause)
        self.model = model


class ConfigError(SummarizerError):
    """Raised when configuration is missing or invalid."""

    def __init__(self, message: str, key: str = None, cause: Exception = None):
        super().__init__(message, cause=cause)
        self.key = key