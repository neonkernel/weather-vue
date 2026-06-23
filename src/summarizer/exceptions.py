"""Custom exception hierarchy for the summarizer application."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""

    def __init__(self, message: str = "", *args):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return self.message


class FetchError(SummarizerError):
    """Raised when article fetching fails (network errors, HTTP errors, timeouts)."""

    def __init__(self, message: str = "", url: str = "", status_code: int = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code

    def __str__(self):
        parts = [self.message]
        if self.url:
            parts.append(f"URL: {self.url}")
        if self.status_code is not None:
            parts.append(f"Status: {self.status_code}")
        return " | ".join(parts)


class ParseError(SummarizerError):
    """Raised when article parsing or text extraction fails."""

    def __init__(self, message: str = "", source: str = ""):
        super().__init__(message)
        self.source = source

    def __str__(self):
        if self.source:
            return f"{self.message} | Source: {self.source}"
        return self.message


class LLMError(SummarizerError):
    """Raised when LLM API calls fail."""

    def __init__(self, message: str = "", model: str = ""):
        super().__init__(message)
        self.model = model

    def __str__(self):
        if self.model:
            return f"{self.message} | Model: {self.model}"
        return self.message


class ConfigError(SummarizerError):
    """Raised when configuration is invalid or missing."""
    pass