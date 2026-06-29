"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract base class that all LLM providers must implement."""

    @abstractmethod
    def complete(self, messages: list, **kwargs) -> str:
        """
        Send messages to the LLM and return the completion text.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles are typically 'system', 'user', or 'assistant'.
            **kwargs: Additional provider-specific parameters such as:
                      - model: str
                      - max_tokens: int
                      - temperature: float

        Returns:
            The completion text as a string.

        Raises:
            LLMError: On any provider-level error (auth, rate limit, etc.)
        """
        ...

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model identifier for this provider."""
        ...

    def count_tokens(self, text: str) -> int:
        """
        Estimate the token count for the given text.

        Providers can override this for more accurate counting.
        Default implementation uses a character-based heuristic (~4 chars/token).

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        return max(1, len(text) // 4)