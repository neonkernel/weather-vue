"""OpenAI provider implementation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from summarizer.exceptions import LLMError
from summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from summarizer.config import SummarizerConfig

DEFAULT_MODEL = "gpt-4o-mini"
FALLBACK_CHARS_PER_TOKEN = 4


class OpenAIProvider(BaseLLMProvider):
    """
    LLM provider backed by the OpenAI Chat Completions API.

    Uses tiktoken for accurate token counting when available,
    falling back to a character-based heuristic otherwise.
    """

    def __init__(self, config: "SummarizerConfig") -> None:
        self._config = config
        api_key = (
            getattr(config, "openai_api_key", None)
            or os.environ.get("OPENAI_API_KEY", "")
        )
        if not api_key:
            raise LLMError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or openai_api_key in config."
            )

        try:
            import openai
            self._client = openai.OpenAI(api_key=api_key)
        except ImportError as exc:
            raise LLMError(
                "openai package is not installed. Run: pip install openai"
            ) from exc

        self._model = (
            getattr(config, "model", None)
            or os.environ.get("DEFAULT_MODEL", DEFAULT_MODEL)
        )
        self._tiktoken_enc = self._load_tiktoken()

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send messages to OpenAI and return the assistant reply."""
        model = kwargs.pop("model", self._model)
        max_tokens = kwargs.pop("max_tokens", getattr(self._config, "max_tokens", 4096))

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(f"OpenAI completion failed: {exc}") from exc

    def get_default_model(self) -> str:
        return self._model or DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        if self._tiktoken_enc is not None:
            return len(self._tiktoken_enc.encode(text))
        return max(1, len(text) // FALLBACK_CHARS_PER_TOKEN)

    def get_provider_name(self) -> str:
        return "openai"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_tiktoken(self):
        """Attempt to load a tiktoken encoder; return None on failure."""
        try:
            import tiktoken
            return tiktoken.encoding_for_model(self._model or DEFAULT_MODEL)
        except Exception:
            try:
                import tiktoken
                return tiktoken.get_encoding("cl100k_base")
            except Exception:
                return None