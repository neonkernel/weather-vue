"""OpenAI LLM provider."""

from __future__ import annotations

import logging
from typing import Any

from ...exceptions import LLMError
from ..base import BaseLLMProvider

logger = logging.getLogger(__name__)

_TIKTOKEN_AVAILABLE = False
try:
    import tiktoken  # type: ignore

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    pass

_DEFAULT_MODEL = "gpt-4o"
# Fallback chars-per-token ratio when tiktoken is unavailable
_CHARS_PER_TOKEN = 4


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> None:
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise LLMError(
                "The 'openai' package is required for OpenAIProvider. "
                "Install it with: pip install openai"
            ) from exc

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model or _DEFAULT_MODEL
        self._temperature = temperature
        self._max_tokens = max_tokens

        # Pre-load tiktoken encoding if available
        self._encoding = None
        if _TIKTOKEN_AVAILABLE:
            try:
                self._encoding = tiktoken.encoding_for_model(self._model)
            except KeyError:
                # Fall back to cl100k_base for unknown models
                self._encoding = tiktoken.get_encoding("cl100k_base")

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return _DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        import openai  # type: ignore

        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", self._temperature)
        max_tokens = kwargs.pop("max_tokens", self._max_tokens)

        logger.debug(
            "OpenAI request | model=%s temperature=%s max_tokens=%s messages=%d",
            model,
            temperature,
            max_tokens,
            len(messages),
        )

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except openai.AuthenticationError as exc:
            raise LLMError(f"OpenAI authentication failed: {exc}") from exc
        except openai.RateLimitError as exc:
            raise LLMError(f"OpenAI rate limit exceeded: {exc}") from exc
        except openai.BadRequestError as exc:
            raise LLMError(f"OpenAI bad request: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise LLMError(f"OpenAI connection error: {exc}") from exc
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling OpenAI: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            raise LLMError("OpenAI returned an empty response content.")
        return content