"""Base class for all LLM providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract base class defining the interface all LLM providers must implement."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send messages to the LLM and return the completion text.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles are typically 'system', 'user', 'assistant'.
            **kwargs: Additional provider-specific parameters (temperature, max_tokens, etc.)

        Returns:
            The text content of the LLM's response.

        Raises:
            LLMError: If the request fails for any reason.
        """
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.

        Args:
            text: The text to count tokens for.

        Returns:
            Estimated token count.
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
        """Return the canonical provider name string."""
        ...