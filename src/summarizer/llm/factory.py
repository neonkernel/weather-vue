"""Factory for creating LLM provider instances from configuration."""

from typing import TYPE_CHECKING

from ..exceptions import LLMError
from ..logger import get_logger
from .base import BaseLLMProvider
from .providers import AnthropicProvider, OllamaProvider, OpenAIProvider

if TYPE_CHECKING:
    from ..config import Config

logger = get_logger(__name__)

# Canonical provider names
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OLLAMA = "ollama"

SUPPORTED_PROVIDERS = (PROVIDER_OPENAI, PROVIDER_ANTHROPIC, PROVIDER_OLLAMA)


class ProviderFactory:
    """Creates and configures LLM provider instances."""

    @staticmethod
    def create(config: "Config") -> BaseLLMProvider:
        """
        Instantiate the correct provider based on *config.provider*.

        Args:
            config: Application configuration object.

        Returns:
            A fully-initialised :class:`BaseLLMProvider` instance.

        Raises:
            LLMError: If the provider name is unknown or required credentials
                      are missing.
        """
        provider_name = (config.provider or PROVIDER_OPENAI).lower().strip()
        logger.info("Creating LLM provider: %s", provider_name)

        if provider_name == PROVIDER_OPENAI:
            return ProviderFactory._create_openai(config)
        elif provider_name == PROVIDER_ANTHROPIC:
            return ProviderFactory._create_anthropic(config)
        elif provider_name == PROVIDER_OLLAMA:
            return ProviderFactory._create_ollama(config)
        else:
            raise LLMError(
                f"Unknown LLM provider '{provider_name}'. "
                f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_openai(config: "Config") -> OpenAIProvider:
        api_key = config.openai_api_key
        if not api_key:
            raise LLMError(
                "OpenAI API key is required. Set OPENAI_API_KEY or pass --openai-api-key."
            )
        return OpenAIProvider(
            api_key=api_key,
            model=config.model or None,
        )

    @staticmethod
    def _create_anthropic(config: "Config") -> AnthropicProvider:
        api_key = config.anthropic_api_key
        if not api_key:
            raise LLMError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY or pass --anthropic-api-key."
            )
        return AnthropicProvider(
            api_key=api_key,
            model=config.model or None,
        )

    @staticmethod
    def _create_ollama(config: "Config") -> OllamaProvider:
        host = config.ollama_host or None
        return OllamaProvider(
            host=host,
            model=config.model or None,
        )