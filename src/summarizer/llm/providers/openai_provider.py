"""OpenAI LLM provider."""

from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from src.summarizer.config import Config


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI API."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, config: "Config | None" = None) -> None:
        self._config = config
        api_key = (
            (config.openai_api_key if config and hasattr(config, "openai_api_key") else None)
            or os.environ.get("OPENAI_API_KEY")
        )
        if not api_key:
            raise LLMError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or provide it in the config."
            )
        try:
            import openai
        except ImportError as exc:
            raise LLMError(
                "The 'openai' package is required for the OpenAI provider. "
                "Install it with: pip install openai"
            ) from exc

        self._client = openai.OpenAI(api_key=api_key)
        self._model = (
            (config.model if config and hasattr(config, "model") and config.model else None)
            or os.environ.get("DEFAULT_MODEL")
            or self.DEFAULT_MODEL
        )

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        """Use tiktoken for accurate OpenAI token counting."""
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model(self._model)
            return len(enc.encode(text))
        except Exception:
            # Fallback heuristic: ~4 characters per token
            return max(1, len(text) // 4)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send a chat completion request to OpenAI."""
        model = kwargs.pop("model", self._model)
        max_tokens = kwargs.pop("max_tokens", None)
        if max_tokens is None and self._config and hasattr(self._config, "max_tokens"):
            max_tokens = self._config.max_tokens
        temperature = kwargs.pop("temperature", 0.3)

        try:
            request_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **kwargs,
            }
            if max_tokens is not None:
                request_kwargs["max_tokens"] = max_tokens

            response = self._client.chat.completions.create(**request_kwargs)
            content = response.choices[0].message.content
            if content is None:
                raise LLMError("OpenAI returned an empty response.")
            return content
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc