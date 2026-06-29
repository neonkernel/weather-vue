"""Custom exceptions for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """Raised when an LLM provider encounters an error."""


class ConfigError(SummarizerError):
    """Raised for invalid or missing configuration."""


class IngestionError(SummarizerError):
    """Raised when content ingestion fails."""


class ChunkingError(SummarizerError):
    """Raised when text chunking fails."""