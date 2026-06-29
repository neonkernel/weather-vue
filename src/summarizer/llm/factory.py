"""Factory for creating LLM provider instances."""
import os
from typing import Optional

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider


class ProviderFactory:
    """Maps provider name strings to provider classes and instantiates them with config."""

    _PROVIDER_MAP: dict[str, str] = {
        "openai": "src.summarizer.llm.providers.openai_provider.OpenAIProvider",
        "anthropic": "src.summarizer.llm.providers.anthropic_provider.AnthropicProvider",
        "ollama": "src.summarizer.llm.providers.ollama_provider.OllamaProvider",
    }

    @classmethod
    def create(
        cls,
        provider_name: Optional[str] = None,
        config: Optional[Config] = None,
    ) -> BaseLLMProvider:
        """
        Create and return the appropriate LLM provider instance.

        Provider resolution order:
        1. Explicit `provider_name` argument
        2. `config.provider` field
        3. `LLM_PROVIDER` environment variable
        4. Default to 'openai'

        Args:
            provider_name: Optional explicit provider name ('openai', 'anthropic', 'ollama').
            config: Optional Config instance to pull settings from.

        Returns:
            A fully-configured BaseLLMProvider instance.

        Raises:
            LLMError: If the provider name is unknown or instantiation fails.
        """
        resolved_name = (
            provider_name
            or (config.provider if config and config.provider else None)
            or os.environ.get("LLM_PROVIDER")
            or "openai"
        ).lower().strip()

        if resolved_name not in cls._PROVIDER_MAP:
            available = ", ".join(sorted(cls._PROVIDER_MAP.keys()))
            raise LLMError(
                f"Unknown LLM provider '{resolved_name}'. "
                f"Available providers: {available}"
            )

        # Lazy import to avoid pulling in optional dependencies unless needed
        module_path, class_name = cls._PROVIDER_MAP[resolved_name].rsplit(".", 1)
        try:
            import importlib
            module = importlib.import_module(module_path)
            provider_class = getattr(module, class_name)
        except ImportError as exc:
            raise LLMError(
                f"Failed to import provider '{resolved_name}': {exc}. "
                f"Make sure the required dependencies are installed."
            ) from exc
        except AttributeError as exc:
            raise LLMError(
                f"Provider class '{class_name}' not found in module '{module_path}': {exc}"
            ) from exc

        try:
            return provider_class(config=config)
        except Exception as exc:
            raise LLMError(
                f"Failed to instantiate provider '{resolved_name}': {exc}"
            ) from exc

    @classmethod
    def available_providers(cls) -> list[str]:
        """Return a sorted list of all registered provider names."""
        return sorted(cls._PROVIDER_MAP.keys())