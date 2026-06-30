"""Provider factory for instantiating LLM providers from config."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from src.summarizer.config import Config


_PROVIDER_MAP: dict[str, str] = {
    "openai": "src.summarizer.llm.providers.openai_provider.OpenAIProvider",
    "anthropic": "src.summarizer.llm.providers.anthropic_provider.AnthropicProvider",
    "ollama": "src.summarizer.llm.providers.ollama_provider.OllamaProvider",
}


def _import_provider(dotted_path: str) -> type[BaseLLMProvider]:
    """Dynamically import a provider class from a dotted module path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class ProviderFactory:
    """Creates and returns configured LLM provider instances."""

    @staticmethod
    def get_provider(config: "Config | None" = None, provider_name: str | None = None) -> BaseLLMProvider:
        """
        Instantiate and return the appropriate LLM provider.

        Resolution order for provider name:
            1. Explicit ``provider_name`` argument
            2. ``config.provider`` field
            3. ``LLM_PROVIDER`` environment variable
            4. Defaults to ``"openai"``

        Args:
            config: Optional Config object.
            provider_name: Explicit provider override.

        Returns:
            An instantiated BaseLLMProvider.

        Raises:
            LLMError: If the provider name is unrecognized.
        """
        name = (
            provider_name
            or (config.provider if config and hasattr(config, "provider") else None)
            or os.environ.get("LLM_PROVIDER", "openai")
        ).lower().strip()

        if name not in _PROVIDER_MAP:
            raise LLMError(
                f"Unknown LLM provider: '{name}'. "
                f"Valid choices are: {', '.join(sorted(_PROVIDER_MAP.keys()))}"
            )

        provider_cls = _import_provider(_PROVIDER_MAP[name])
        return provider_cls(config=config)  # type: ignore[call-arg]