"""Factory for creating LLM provider instances from configuration."""

from typing import TYPE_CHECKING

from src.summarizer.exceptions import LLMError
from src.summarizer.logger import get_logger

if TYPE_CHECKING:
    from src.summarizer.config import Config
    from src.summarizer.llm.base import BaseLLMProvider

logger = get_logger(__name__)

PROVIDER_NAMES = ("openai", "anthropic", "ollama")


class ProviderFactory:
    """Creates the appropriate LLM provider from a Config object."""

    @staticmethod
    def create(config: "Config") -> "BaseLLMProvider":
        """
        Instantiate and return the LLM provider specified in *config*.

        The provider is determined by ``config.provider`` (which itself
        honours the ``--provider`` CLI flag and the ``LLM_PROVIDER``
        environment variable).

        Args:
            config: Application configuration object.

        Returns:
            A concrete :class:`BaseLLMProvider` instance.

        Raises:
            LLMError: If the provider name is unknown or instantiation fails.
        """
        provider_name = (config.provider or "openai").lower().strip()
        logger.debug("ProviderFactory: creating provider '%s'", provider_name)

        if provider_name == "openai":
            return ProviderFactory._create_openai(config)
        elif provider_name == "anthropic":
            return ProviderFactory._create_anthropic(config)
        elif provider_name == "ollama":
            return ProviderFactory._create_ollama(config)
        else:
            raise LLMError(
                f"Unknown LLM provider '{provider_name}'. "
                f"Valid choices are: {', '.join(PROVIDER_NAMES)}"
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_openai(config: "Config") -> "BaseLLMProvider":
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        api_key = getattr(config, "openai_api_key", None) or ""
        model = getattr(config, "model", None)
        max_tokens = getattr(config, "max_tokens", 4096)
        temperature = getattr(config, "temperature", 0.3)

        return OpenAIProvider(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @staticmethod
    def _create_anthropic(config: "Config") -> "BaseLLMProvider":
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider

        api_key = getattr(config, "anthropic_api_key", None) or ""
        model = getattr(config, "model", None)
        max_tokens = getattr(config, "max_tokens", 4096)
        temperature = getattr(config, "temperature", 0.3)

        return AnthropicProvider(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @staticmethod
    def _create_ollama(config: "Config") -> "BaseLLMProvider":
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        host = getattr(config, "ollama_host", None)
        model = getattr(config, "model", None)
        max_tokens = getattr(config, "max_tokens", 4096)
        temperature = getattr(config, "temperature", 0.3)

        return OllamaProvider(
            host=host,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )