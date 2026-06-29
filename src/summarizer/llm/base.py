"""Abstract base class for LLM providers."""
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
                      Roles can be 'system', 'user', or 'assistant'.
            **kwargs: Additional provider-specific parameters (e.g., temperature,
                      max_tokens, model override).

        Returns:
            The generated text response as a string.

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
        """Return the canonical name for this provider (e.g., 'openai')."""
        ...