"""OpenAI LLM provider implementation."""
from __future__ import annotations

import os
from typing import Any, Optional

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI API."""

    DEFAULT_MODEL = "gpt-4o-mini"
    _TIKTOKEN_ENCODING = "cl100k_base"  # works for gpt-3.5/4/4o family

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config
        self._api_key = self._resolve_api_key()
        self._model = self._resolve_model()
        self._client = self._build_client()

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Call the OpenAI Chat Completions API and return the response text."""
        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", 0.3)
        max_tokens = kwargs.pop("max_tokens", 1024)

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise self._map_error(exc) from exc

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken (exact for OpenAI models)."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding(self._TIKTOKEN_ENCODING)
            return len(enc.encode(text))
        except ImportError:
            # Fallback: rough approximation (1 token ≈ 4 chars)
            return max(1, len(text) // 4)
        except Exception:
            return max(1, len(text) // 4)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> str:
        key = (
            (self._config.openai_api_key if self._config and hasattr(self._config, "openai_api_key") else None)
            or os.environ.get("OPENAI_API_KEY")
            or ""
        )
        if not key:
            raise LLMError(
                "OpenAI API key not found. Set OPENAI_API_KEY env var or provide it in config."
            )
        return key

    def _resolve_model(self) -> str:
        return (
            (self._config.openai_model if self._config and hasattr(self._config, "openai_model") else None)
            or os.environ.get("OPENAI_MODEL")
            or self.DEFAULT_MODEL
        )

    def _build_client(self):
        try:
            import openai
            return openai.OpenAI(api_key=self._api_key)
        except ImportError as exc:
            raise LLMError(
                "The 'openai' package is required for the OpenAI provider. "
                "Install it with: pip install openai"
            ) from exc

    @staticmethod
    def _map_error(exc: Exception) -> LLMError:
        """Map OpenAI SDK exceptions to LLMError."""
        try:
            import openai
            if isinstance(exc, openai.AuthenticationError):
                return LLMError(f"OpenAI authentication failed: {exc}")
            if isinstance(exc, openai.RateLimitError):
                return LLMError(f"OpenAI rate limit exceeded: {exc}")
            if isinstance(exc, openai.APIConnectionError):
                return LLMError(f"OpenAI connection error: {exc}")
            if isinstance(exc, openai.APIStatusError):
                return LLMError(f"OpenAI API error (status {exc.status_code}): {exc}")
        except ImportError:
            pass
        return LLMError(f"OpenAI provider error: {exc}")