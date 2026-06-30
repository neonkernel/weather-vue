"""Base LLM provider abstract class."""

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
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            The text response from the LLM.

        Raises:
            LLMError: On any provider-side error.
        """
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model name for this provider."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text.

        Args:
            text: The text to count tokens for.

        Returns:
            Estimated token count.
        """
        ...