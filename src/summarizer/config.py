"""Configuration management for the summarizer."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Application configuration.

    Attributes:
        openai_api_key: OpenAI API key.
        openai_base_url: Optional custom base URL for OpenAI-compatible endpoints.
        default_model: Default model to use for summarization.
        default_temperature: Default sampling temperature.
        default_max_tokens: Default maximum completion tokens.
        log_level: Logging level.
    """
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    default_model: str = "gpt-4o-mini"
    default_temperature: float = 0.3
    default_max_tokens: int = 1024
    log_level: str = "INFO"


_config: Optional[Config] = None


def get_config() -> Config:
    """Get the application configuration.

    Reads from environment variables if not already configured.

    Returns:
        The application Config instance.
    """
    global _config
    if _config is None:
        _config = Config(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openai_base_url=os.environ.get("OPENAI_BASE_URL"),
            default_model=os.environ.get("SUMMARIZER_MODEL", "gpt-4o-mini"),
            default_temperature=float(os.environ.get("SUMMARIZER_TEMPERATURE", "0.3")),
            default_max_tokens=int(os.environ.get("SUMMARIZER_MAX_TOKENS", "1024")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
    return _config


def reset_config() -> None:
    """Reset the configuration (useful for testing)."""
    global _config
    _config = None


def configure(
    openai_api_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    default_model: str = "gpt-4o-mini",
    default_temperature: float = 0.3,
    default_max_tokens: int = 1024,
    log_level: str = "INFO",
) -> Config:
    """Explicitly configure the application.

    Args:
        openai_api_key: OpenAI API key.
        openai_base_url: Optional custom base URL.
        default_model: Default model name.
        default_temperature: Default sampling temperature.
        default_max_tokens: Default max completion tokens.
        log_level: Logging level string.

    Returns:
        The configured Config instance.
    """
    global _config
    _config = Config(
        openai_api_key=openai_api_key or os.environ.get("OPENAI_API_KEY"),
        openai_base_url=openai_base_url or os.environ.get("OPENAI_BASE_URL"),
        default_model=default_model,
        default_temperature=default_temperature,
        default_max_tokens=default_max_tokens,
        log_level=log_level,
    )
    return _config