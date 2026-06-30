"""Shared exception hierarchy for the summarizer package."""


class SummarizerError(Exception):
    """Base exception for all summarizer errors."""


class LLMError(SummarizerError):
    """Raised when an LLM provider call fails for any reason."""


class IngestionError(SummarizerError):
    """Raised when document ingestion or parsing fails."""


class ConfigError(SummarizerError):
    """Raised for invalid or missing configuration."""


class ChunkingError(SummarizerError):
    """Raised when text chunking fails."""