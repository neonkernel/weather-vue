"""Factory for creating LLM provider instances."""

import os
from typing import TYPE_CHECKING

from ..exceptions import LLMError
from .base import BaseLLMProvider

if TYPE_CHECKING:
    from ..config import Config


PROVIDER_MAP = {
    "openai": "src.summarizer.llm.providers.openai_provider.OpenAIProvider",
    "anthropic": "src.summarizer.llm.providers.anthropic_provider.AnthropicProvider",
    "ollama": "src.summarizer.llm.providers.ollama_provider.OllamaProvider",
}


class ProviderFactory:
    """Creates and returns the appropriate LLM provider based on configuration."""

    @staticmethod
    def create(config: "Config") -> BaseLLMProvider:
        """
        Instantiate and return the correct provider based on config.

        Priority:
            1. config.provider (set by CLI --provider flag or config file)
            2. LLM_PROVIDER environment variable
            3. Default to 'openai'

        Args:
            config: Application configuration object.

        Returns:
            An instantiated BaseLLMProvider implementation.

        Raises:
            LLMError: If the provider name is unknown or instantiation fails.
        """
        provider_name = (
            getattr(config, "provider", None)
            or os.environ.get("LLM_PROVIDER", "openai")
        ).lower().strip()

        if provider_name not in PROVIDER_MAP:
            available = ", ".join(sorted(PROVIDER_MAP.keys()))
            raise LLMError(
                f"Unknown provider '{provider_name}'. Available providers: {available}"
            )

        # Lazy import to avoid pulling in optional dependencies at module load
        module_path, class_name = PROVIDER_MAP[provider_name].rsplit(".", 1)

        # Convert dotted path to importlib-style import
        import importlib
        # Strip leading "src." for relative package imports
        import_path = module_path.replace("src.", "", 1)
        try:
            module = importlib.import_module(f"summarizer.llm.providers.{provider_name}_provider")
        except ImportError as exc:
            raise LLMError(
                f"Could not import provider '{provider_name}': {exc}. "
                "Make sure the required dependencies are installed."
            ) from exc

        provider_class = getattr(module, class_name)

        try:
            return provider_class(config)
        except Exception as exc:
            raise LLMError(
                f"Failed to instantiate provider '{provider_name}': {exc}"
            ) from exc

    @staticmethod
    def available_providers() -> list:
        """Return a list of known provider names."""
        return sorted(PROVIDER_MAP.keys())