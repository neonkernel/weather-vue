"""Factory for creating LLM provider instances."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from summarizer.exceptions import LLMError

if TYPE_CHECKING:
    from summarizer.config import SummarizerConfig
    from summarizer.llm.base import BaseLLMProvider

PROVIDER_MAP: dict[str, str] = {
    "openai": "summarizer.llm.providers.openai_provider.OpenAIProvider",
    "anthropic": "summarizer.llm.providers.anthropic_provider.AnthropicProvider",
    "ollama": "summarizer.llm.providers.ollama_provider.OllamaProvider",
}


class ProviderFactory:
    """Maps provider name strings to provider classes and instantiates them with config."""

    @staticmethod
    def create(config: "SummarizerConfig") -> "BaseLLMProvider":
        """
        Create and return the appropriate provider instance.

        Provider is determined by (in order of precedence):
          1. config.provider field
          2. LLM_PROVIDER environment variable
          3. Defaults to 'openai'

        Args:
            config: The SummarizerConfig instance.

        Returns:
            An instantiated BaseLLMProvider subclass.

        Raises:
            LLMError: If the provider name is unknown or cannot be instantiated.
        """
        provider_name = (
            getattr(config, "provider", None)
            or os.environ.get("LLM_PROVIDER", "openai")
        ).lower().strip()

        if provider_name not in PROVIDER_MAP:
            raise LLMError(
                f"Unknown provider '{provider_name}'. "
                f"Valid providers: {', '.join(PROVIDER_MAP.keys())}"
            )

        dotted_path = PROVIDER_MAP[provider_name]
        module_path, class_name = dotted_path.rsplit(".", 1)

        try:
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            raise LLMError(
                f"Failed to load provider '{provider_name}': {exc}"
            ) from exc

        try:
            return cls(config)
        except Exception as exc:
            raise LLMError(
                f"Failed to instantiate provider '{provider_name}': {exc}"
            ) from exc

    @staticmethod
    def list_providers() -> list[str]:
        """Return a list of all registered provider names."""
        return list(PROVIDER_MAP.keys())