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
                      Roles are 'system', 'user', or 'assistant'.
            **kwargs: Provider-specific overrides (e.g., model, max_tokens, temperature).

        Returns:
            The completion text as a string.

        Raises:
            LLMError: On any provider-side or network error.
        """
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text.

        Args:
            text: The input text to count tokens for.

        Returns:
            Estimated token count as an integer.
        """
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model identifier for this provider."""
        ...