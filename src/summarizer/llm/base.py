"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract base class that all LLM providers must implement."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send a list of messages to the LLM and return the completion text.

        Args:
            messages: A list of message dicts with 'role' and 'content' keys.
                      Roles are 'system', 'user', or 'assistant'.
            **kwargs: Additional provider-specific parameters (temperature, max_tokens, etc.)

        Returns:
            The text content of the LLM's response.

        Raises:
            LLMError: On any provider-level error (auth, rate limit, network, etc.)
        """
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text.

        Args:
            text: The text to count tokens for.

        Returns:
            An integer token count estimate.
        """
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model name for this provider."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the canonical name of this provider (e.g. 'openai', 'anthropic', 'ollama')."""
        ...