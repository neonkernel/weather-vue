"""OpenAI LLM provider implementation."""

import os
from typing import Any

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

try:
    from openai import OpenAI, APIError, AuthenticationError, RateLimitError, APIConnectionError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from ..base import BaseLLMProvider
from ...exceptions import LLMError


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider using the official openai SDK."""

    DEFAULT_MODEL = "gpt-4o"
    FALLBACK_CHARS_PER_TOKEN = 4

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            model: Model name to use. Falls back to DEFAULT_MODEL.
            **kwargs: Additional options (currently unused).
        """
        if not HAS_OPENAI:
            raise LLMError(
                "openai package is not installed. Run: pip install openai"
            )

        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise LLMError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable or pass api_key."
            )

        self._model = model or self.DEFAULT_MODEL
        self._client = OpenAI(api_key=resolved_key)

        # Initialise tiktoken encoder once
        self._encoder = None
        if HAS_TIKTOKEN:
            try:
                self._encoder = tiktoken.encoding_for_model(self._model)
            except KeyError:
                try:
                    self._encoder = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    pass

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send messages to OpenAI and return the assistant response text."""
        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", 0.3)
        max_tokens = kwargs.pop("max_tokens", 1024)

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMError("OpenAI returned an empty response.")
            return content

        except AuthenticationError as exc:
            raise LLMError(f"OpenAI authentication failed: {exc}") from exc
        except RateLimitError as exc:
            raise LLMError(f"OpenAI rate limit exceeded: {exc}") from exc
        except APIConnectionError as exc:
            raise LLMError(f"OpenAI connection error: {exc}") from exc
        except APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error from OpenAI provider: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken when available, otherwise use a heuristic."""
        if self._encoder is not None:
            return len(self._encoder.encode(text))
        # Fallback heuristic: ~4 characters per token
        return max(1, len(text) // self.FALLBACK_CHARS_PER_TOKEN)