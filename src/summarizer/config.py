"""Application configuration management."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Holds all runtime configuration for the summarizer."""

    # --- LLM Provider ---
    provider: str = "openai"

    # --- Model settings ---
    model: Optional[str] = None  # None → use provider's default
    max_tokens: int = 4096
    temperature: float = 0.3

    # --- OpenAI ---
    openai_api_key: Optional[str] = None

    # --- Anthropic ---
    anthropic_api_key: Optional[str] = None

    # --- Ollama ---
    ollama_host: str = "http://localhost:11434"

    # --- Summarizer behaviour ---
    style: str = "concise"
    language: str = "en"
    chunk_size: int = 3000   # tokens (approximate)
    chunk_overlap: int = 200  # tokens

    # --- Output ---
    output_format: str = "text"  # text | markdown | json

    @classmethod
    def from_env(cls) -> "Config":
        """
        Build a Config by reading environment variables.

        Environment variables take precedence over dataclass defaults.
        """
        return cls(
            provider=os.environ.get("LLM_PROVIDER", "openai"),
            model=os.environ.get("DEFAULT_MODEL") or None,
            max_tokens=int(os.environ.get("MAX_TOKENS", "4096")),
            temperature=float(os.environ.get("TEMPERATURE", "0.3")),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            ollama_host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            style=os.environ.get("SUMMARY_STYLE", "concise"),
            language=os.environ.get("SUMMARY_LANGUAGE", "en"),
            chunk_size=int(os.environ.get("CHUNK_SIZE", "3000")),
            chunk_overlap=int(os.environ.get("CHUNK_OVERLAP", "200")),
            output_format=os.environ.get("OUTPUT_FORMAT", "text"),
        )

    def update_from_cli(self, args) -> None:
        """
        Overlay CLI argument values onto this config.

        Only non-None / non-default CLI values are applied so that
        environment variables remain the fallback rather than being
        overwritten by argparse defaults.

        Args:
            args: Parsed argparse.Namespace object.
        """
        if getattr(args, "provider", None):
            self.provider = args.provider
        if getattr(args, "model", None):
            self.model = args.model
        if getattr(args, "max_tokens", None) is not None:
            self.max_tokens = args.max_tokens
        if getattr(args, "temperature", None) is not None:
            self.temperature = args.temperature
        if getattr(args, "style", None):
            self.style = args.style
        if getattr(args, "language", None):
            self.language = args.language
        if getattr(args, "output_format", None):
            self.output_format = args.output_format