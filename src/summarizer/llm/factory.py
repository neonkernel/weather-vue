"""Provider factory for instantiating the correct LLM provider from config."""

from typing import TYPE_CHECKING

from .base import BaseLLMProvider
from .providers import AnthropicProvider, OllamaProvider, OpenAIProvider
from ..exceptions import LLMError

if TYPE_CHECKING:
    from ..config import Config

# Registry mapping provider name strings to their classes
PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}


def create_provider(config: "Config") -> BaseLLMProvider:
    """
    Instantiate and return the correct LLM provider based on the given config.

    The provider is determined by ``config.provider``.  Each provider is
    constructed with the relevant credentials and model name from config.

    Args:
        config: Application config object with provider settings.

    Returns:
        An instantiated :class:`BaseLLMProvider`.

    Raises:
        LLMError: If the provider name is unknown or instantiation fails.
    """
    provider_name = (config.provider or "openai").lower().strip()

    provider_class = PROVIDER_REGISTRY.get(provider_name)
    if provider_class is None:
        available = ", ".join(sorted(PROVIDER_REGISTRY.keys()))
        raise LLMError(
            f"Unknown LLM provider '{provider_name}'. "
            f"Available providers: {available}"
        )

    try:
        if provider_name == "openai":
            return OpenAIProvider(
                api_key=getattr(config, "openai_api_key", None),
                model=getattr(config, "model", None),
            )

        if provider_name == "anthropic":
            return AnthropicProvider(
                api_key=getattr(config, "anthropic_api_key", None),
                model=getattr(config, "model", None),
            )

        if provider_name == "ollama":
            return OllamaProvider(
                host=getattr(config, "ollama_host", None),
                model=getattr(config, "model", None),
            )

        # Generic fallback (should not be reached due to registry check above)
        raise LLMError(f"No constructor defined for provider '{provider_name}'.")

    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(
            f"Failed to initialise '{provider_name}' provider: {exc}"
        ) from exc


class ProviderFactory:
    """
    Factory class for creating LLM providers.

    Prefer the module-level :func:`create_provider` function for simple use-cases.
    Use this class when you need to register custom providers at runtime.
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[BaseLLMProvider]] = dict(PROVIDER_REGISTRY)

    def register(self, name: str, cls: type[BaseLLMProvider]) -> None:
        """Register a custom provider class under the given name."""
        self._registry[name] = cls

    def create(self, config: "Config") -> BaseLLMProvider:
        """Create a provider instance from config using this factory's registry."""
        provider_name = (config.provider or "openai").lower().strip()
        provider_class = self._registry.get(provider_name)
        if provider_class is None:
            available = ", ".join(sorted(self._registry.keys()))
            raise LLMError(
                f"Unknown LLM provider '{provider_name}'. "
                f"Available providers: {available}"
            )
        return create_provider(config)

    @property
    def available_providers(self) -> list[str]:
        """Return a sorted list of registered provider names."""
        return sorted(self._registry.keys())