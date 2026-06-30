"""Provider factory — maps provider names to concrete provider instances."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from ..exceptions import LLMError
from .base import BaseLLMProvider

if TYPE_CHECKING:
    from ..config import SummarizerConfig

logger = logging.getLogger(__name__)

_PROVIDER_NAMES = ("openai", "anthropic", "ollama")


class ProviderFactory:
    """Creates and returns the correct :class:`BaseLLMProvider` for a given name."""

    @staticmethod
    def create(provider_name: str | None = None, config: "SummarizerConfig | None" = None) -> BaseLLMProvider:
        """
        Instantiate the requested LLM provider.

        Resolution order for ``provider_name``:
        1. Explicit ``provider_name`` argument
        2. ``config.provider`` (if config is supplied)
        3. ``LLM_PROVIDER`` environment variable
        4. Falls back to ``"openai"``

        Args:
            provider_name: One of ``"openai"``, ``"anthropic"``, or ``"ollama"``.
            config: Optional :class:`SummarizerConfig` instance.

        Returns:
            A concrete :class:`BaseLLMProvider` instance.

        Raises:
            LLMError: If the provider name is unknown or required credentials
                      are missing.
        """
        resolved_name = (
            provider_name
            or (config.provider if config is not None else None)
            or os.getenv("LLM_PROVIDER", "openai")
        ).lower()

        if resolved_name not in _PROVIDER_NAMES:
            raise LLMError(
                f"Unknown provider '{resolved_name}'. "
                f"Valid choices are: {', '.join(_PROVIDER_NAMES)}"
            )

        logger.debug("ProviderFactory: creating provider '%s'", resolved_name)

        if resolved_name == "openai":
            return ProviderFactory._make_openai(config)
        if resolved_name == "anthropic":
            return ProviderFactory._make_anthropic(config)
        if resolved_name == "ollama":
            return ProviderFactory._make_ollama(config)

        # Should never reach here, but keeps type checkers happy
        raise LLMError(f"Unhandled provider: {resolved_name}")

    # ------------------------------------------------------------------
    # Private factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_openai(config: "SummarizerConfig | None") -> BaseLLMProvider:
        from .providers.openai_provider import OpenAIProvider

        api_key = (
            (config.openai_api_key if config is not None else None)
            or os.getenv("OPENAI_API_KEY", "")
        )
        if not api_key:
            raise LLMError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or provide it in the config."
            )

        model = (config.default_model if config is not None else None) or None
        temperature = (config.temperature if config is not None else 0.3) or 0.3
        max_tokens = (config.max_tokens if config is not None else 4096) or 4096

        return OpenAIProvider(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def _make_anthropic(config: "SummarizerConfig | None") -> BaseLLMProvider:
        from .providers.anthropic_provider import AnthropicProvider

        api_key = (
            (config.anthropic_api_key if config is not None else None)
            or os.getenv("ANTHROPIC_API_KEY", "")
        )
        if not api_key:
            raise LLMError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable "
                "or provide it in the config."
            )

        model = (config.default_model if config is not None else None) or None
        temperature = (config.temperature if config is not None else 0.3) or 0.3
        max_tokens = (config.max_tokens if config is not None else 4096) or 4096

        return AnthropicProvider(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def _make_ollama(config: "SummarizerConfig | None") -> BaseLLMProvider:
        from .providers.ollama_provider import OllamaProvider

        host = (
            (config.ollama_host if config is not None else None)
            or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        )
        model = (config.default_model if config is not None else None) or None
        temperature = (config.temperature if config is not None else 0.3) or 0.3
        max_tokens = (config.max_tokens if config is not None else 4096) or 4096

        return OllamaProvider(
            host=host,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )