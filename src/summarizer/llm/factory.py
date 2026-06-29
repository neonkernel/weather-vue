"""Factory for instantiating LLM providers from config or CLI flags."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.summarizer.exceptions import LLMError

if TYPE_CHECKING:
    from src.summarizer.config import Config
    from src.summarizer.llm.base import BaseLLMProvider

PROVIDER_REGISTRY: dict[str, str] = {
    "openai": "src.summarizer.llm.providers.openai_provider.OpenAIProvider",
    "anthropic": "src.summarizer.llm.providers.anthropic_provider.AnthropicProvider",
    "ollama": "src.summarizer.llm.providers.ollama_provider.OllamaProvider",
}


class ProviderFactory:
    """Creates and returns an LLM provider instance based on configuration."""

    @staticmethod
    def _import_provider(dotted_path: str) -> type:
        """Dynamically import a provider class from a dotted module path."""
        module_path, class_name = dotted_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    @classmethod
    def from_config(cls, config: "Config") -> "BaseLLMProvider":
        """
        Instantiate the appropriate provider from a Config object.

        Provider resolution order:
        1. config.provider (set from --provider CLI flag)
        2. LLM_PROVIDER environment variable
        3. Default: 'openai'
        """
        provider_name = (
            getattr(config, "provider", None)
            or os.environ.get("LLM_PROVIDER", "openai")
        ).lower().strip()

        return cls.create(provider_name, config)

    @classmethod
    def create(cls, provider_name: str, config: "Config") -> "BaseLLMProvider":
        """
        Instantiate a provider by name.

        Args:
            provider_name: One of 'openai', 'anthropic', 'ollama'.
            config: Application config object.

        Returns:
            An instance of the requested provider.

        Raises:
            LLMError: If provider_name is not recognised.
        """
        provider_name = provider_name.lower().strip()

        if provider_name not in PROVIDER_REGISTRY:
            available = ", ".join(sorted(PROVIDER_REGISTRY.keys()))
            raise LLMError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {available}"
            )

        provider_cls = cls._import_provider(PROVIDER_REGISTRY[provider_name])
        return provider_cls(config)