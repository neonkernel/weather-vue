"""Custom exception hierarchy for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""

    def __init__(self, message: str = "", *args):
        self.message = message
        super().__init__(message, *args)

    def __str__(self):
        return self.message


class FetchError(SummarizerError):
    """Raised when an article cannot be fetched from a URL or network resource."""

    def __init__(self, message: str = "", url: str = "", status_code: int = None):
        self.url = url
        self.status_code = status_code
        super().__init__(message)


class ParseError(SummarizerError):
    """Raised when article content cannot be parsed or extracted."""

    def __init__(self, message: str = "", source: str = ""):
        self.source = source
        super().__init__(message)


class LLMError(SummarizerError):
    """Raised when the LLM API call fails."""

    def __init__(self, message: str = "", model: str = ""):
        self.model = model
        super().__init__(message)


class ConfigError(SummarizerError):
    """Raised when configuration is invalid or missing."""
    pass