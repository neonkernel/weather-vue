"""ProviderFactory: maps provider names to provider classes and instantiates them."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..exceptions import LLMError
from ..logger import get_logger
from .base import BaseLLMProvider

if TYPE_CHECKING:
    from ..config import SummarizerConfig

logger = get_logger(__name__)

# Lazy imports to avoid hard failures when optional packages aren't installed
_PROVIDER_MAP: dict[str, str] = {
    "openai": "src.summarizer.llm.providers.openai_provider.OpenAIProvider",
    "anthropic": "src.summarizer.llm.providers.anthropic_provider.AnthropicProvider",
    "ollama": "src.summarizer.llm.providers.ollama_provider.OllamaProvider",
}

SUPPORTED_PROVIDERS = list(_PROVIDER_MAP.keys())


class ProviderFactory:
    """
    Factory that creates the appropriate BaseLLMProvider given a config object.

    Provider resolution order:
    1. ``config.provider`` field (set from --provider CLI flag or LLM_PROVIDER env var)
    2. Falls back to 'openai' if not set.
    """

    @staticmethod
    def create(config: "SummarizerConfig") -> BaseLLMProvider:
        """
        Instantiate and return the correct LLM provider from config.

        Args:
            config: A SummarizerConfig instance containing provider settings.

        Returns:
            An instance of a BaseLLMProvider subclass.

        Raises:
            LLMError: If the provider name is unsupported or instantiation fails.
        """
        provider_name = (getattr(config, "provider", None) or "openai").lower().strip()

        if provider_name not in SUPPORTED_PROVIDERS:
            raise LLMError(
                f"Unsupported provider '{provider_name}'. "
                f"Choose from: {', '.join(SUPPORTED_PROVIDERS)}"
            )

        logger.debug("ProviderFactory: creating provider '%s'", provider_name)

        if provider_name == "openai":
            return ProviderFactory._create_openai(config)
        elif provider_name == "anthropic":
            return ProviderFactory._create_anthropic(config)
        elif provider_name == "ollama":
            return ProviderFactory._create_ollama(config)

        # Should never reach here due to the check above
        raise LLMError(f"Provider '{provider_name}' is registered but has no factory method.")

    @staticmethod
    def _create_openai(config: "SummarizerConfig") -> BaseLLMProvider:
        from .providers.openai_provider import OpenAIProvider

        api_key = getattr(config, "openai_api_key", None) or ""
        model = getattr(config, "openai_model", None)

        return OpenAIProvider(api_key=api_key, model=model)

    @staticmethod
    def _create_anthropic(config: "SummarizerConfig") -> BaseLLMProvider:
        from .providers.anthropic_provider import AnthropicProvider

        api_key = getattr(config, "anthropic_api_key", None) or ""
        model = getattr(config, "anthropic_model", None)

        return AnthropicProvider(api_key=api_key, model=model)

    @staticmethod
    def _create_ollama(config: "SummarizerConfig") -> BaseLLMProvider:
        from .providers.ollama_provider import OllamaProvider

        host = getattr(config, "ollama_host", None)
        model = getattr(config, "ollama_model", None)

        return OllamaProvider(host=host, model=model)