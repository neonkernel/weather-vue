"""Base abstract class for LLM providers."""

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
                      Roles are typically 'system', 'user', or 'assistant'.
            **kwargs: Additional provider-specific parameters (e.g., temperature,
                      max_tokens, model override).

        Returns:
            The text content of the model's response.

        Raises:
            LLMError: On any provider-level error (auth, rate limit, network, etc.)
        """
        ...

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model identifier for this provider."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text.

        Args:
            text: The text to count tokens for.

        Returns:
            An integer token count (may be an approximation).
        """
        ...