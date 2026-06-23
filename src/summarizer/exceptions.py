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
    """Raised when an article cannot be fetched from a URL or file.

    Attributes:
        source: The URL or file path that failed to fetch.
        status_code: HTTP status code if applicable.
    """

    def __init__(self, message: str, source: str = "", status_code: int = None, cause: Exception = None):
        super().__init__(message, cause)
        self.source = source
        self.status_code = status_code


class ParseError(SummarizerError):
    """Raised when article text cannot be extracted from HTML or other content.

    Attributes:
        source: The URL or file path that failed to parse.
    """

    def __init__(self, message: str, source: str = "", cause: Exception = None):
        super().__init__(message, cause)
        self.source = source


class LLMError(SummarizerError):
    """Raised when the LLM API call fails or returns invalid output."""

    def __init__(self, message: str, model: str = "", cause: Exception = None):
        super().__init__(message, cause)
        self.model = model


class ConfigError(SummarizerError):
    """Raised when configuration is missing or invalid."""

    def __init__(self, message: str, key: str = "", cause: Exception = None):
        super().__init__(message, cause)
        self.key = key