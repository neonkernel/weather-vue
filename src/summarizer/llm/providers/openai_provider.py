"""OpenAI LLM provider implementation."""

import os
from typing import TYPE_CHECKING, Any

from ...exceptions import LLMError
from ..base import BaseLLMProvider

if TYPE_CHECKING:
    from ...config import Config

# Default models
DEFAULT_MODEL = "gpt-4o-mini"
FALLBACK_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI API."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.api_key = (
            getattr(config, "openai_api_key", None)
            or os.environ.get("OPENAI_API_KEY", "")
        )
        if not self.api_key:
            raise LLMError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or provide openai_api_key in config."
            )

        try:
            import openai
        except ImportError as exc:
            raise LLMError(
                "openai package is not installed. Run: pip install openai"
            ) from exc

        self._openai = openai
        self._client = openai.OpenAI(api_key=self.api_key)

    def get_default_model(self) -> str:
        return getattr(self.config, "model", None) or DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        """Use tiktoken for accurate OpenAI token counting."""
        try:
            import tiktoken
            model = self.get_default_model()
            try:
                enc = tiktoken.encoding_for_model(model)
            except KeyError:
                enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            # Fall back to character heuristic if tiktoken not available
            return max(1, len(text) // 4)

    def complete(self, messages: list, **kwargs) -> str:
        """
        Call the OpenAI Chat Completions API.

        Args:
            messages: List of {'role': ..., 'content': ...} dicts.
            **kwargs: Overrides for model, max_tokens, temperature.

        Returns:
            The assistant's reply text.

        Raises:
            LLMError: On API errors.
        """
        model = kwargs.get("model") or self.get_default_model()
        max_tokens = kwargs.get("max_tokens") or getattr(self.config, "max_tokens", 4096)
        temperature = kwargs.get("temperature")
        if temperature is None:
            temperature = getattr(self.config, "temperature", 0.3)

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except self._openai.AuthenticationError as exc:
            raise LLMError(f"OpenAI authentication failed: {exc}") from exc
        except self._openai.RateLimitError as exc:
            raise LLMError(f"OpenAI rate limit exceeded: {exc}") from exc
        except self._openai.BadRequestError as exc:
            raise LLMError(f"OpenAI bad request: {exc}") from exc
        except self._openai.APIConnectionError as exc:
            raise LLMError(f"OpenAI connection error: {exc}") from exc
        except self._openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling OpenAI: {exc}") from exc