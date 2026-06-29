"""OpenAI provider implementation."""
from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from src.summarizer.config import Config

_DEFAULT_MODEL = "gpt-4o-mini"
_FALLBACK_CHARS_PER_TOKEN = 4  # Used when tiktoken is unavailable


def _get_encoding(model: str):
    """Return a tiktoken encoding for the given model, or None on failure."""
    try:
        import tiktoken
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")
    except ImportError:
        return None


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI API."""

    def __init__(self, config: "Config") -> None:
        self._config = config
        self._model = getattr(config, "model", None) or _DEFAULT_MODEL
        api_key = getattr(config, "openai_api_key", None) or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LLMError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or provide openai_api_key in config."
            )
        try:
            import openai as _openai
            self._client = _openai.OpenAI(api_key=api_key)
        except ImportError as exc:
            raise LLMError(
                "The 'openai' package is required for the OpenAI provider. "
                "Install it with: pip install openai"
            ) from exc

        self._encoding = _get_encoding(self._model)

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    @property
    def default_model(self) -> str:
        return _DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    def count_tokens(self, text: str) -> int:
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        return max(1, len(text) // _FALLBACK_CHARS_PER_TOKEN)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the OpenAI Chat Completions API.

        Args:
            messages: List of {'role': ..., 'content': ...} dicts.
            **kwargs: Overrides for model, temperature, max_tokens.

        Returns:
            Assistant message content string.

        Raises:
            LLMError: Wraps any openai SDK exception.
        """
        try:
            import openai
        except ImportError as exc:
            raise LLMError("openai package not installed") from exc

        model = kwargs.pop("model", None) or self._model
        temperature = kwargs.pop(
            "temperature",
            getattr(self._config, "temperature", 0.3),
        )
        max_tokens = kwargs.pop(
            "max_tokens",
            getattr(self._config, "max_tokens", 4096),
        )

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

        except openai.AuthenticationError as exc:
            raise LLMError(f"OpenAI authentication failed: {exc}") from exc
        except openai.RateLimitError as exc:
            raise LLMError(f"OpenAI rate limit exceeded: {exc}") from exc
        except openai.BadRequestError as exc:
            raise LLMError(f"OpenAI bad request: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise LLMError(f"OpenAI connection error: {exc}") from exc
        except openai.APIStatusError as exc:
            raise LLMError(f"OpenAI API error ({exc.status_code}): {exc.message}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected OpenAI error: {exc}") from exc