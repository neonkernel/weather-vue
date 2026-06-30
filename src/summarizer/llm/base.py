"""Base abstract class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract base class that all LLM providers must implement."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send messages to the LLM and return the completion text.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles are typically 'system', 'user', and 'assistant'.
            **kwargs: Additional provider-specific parameters (e.g., temperature,
                      max_tokens, model).

        Returns:
            The text content of the LLM's response.

        Raises:
            LLMError: On any provider-level error (auth, rate limit, network, etc.)
        """
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a string of text.

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
        """Return the canonical name of this provider."""
        ...