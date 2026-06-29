"""Anthropic Claude LLM provider implementation."""
from __future__ import annotations

import os
from typing import Any, Optional

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """LLM provider backed by the Anthropic Claude API."""

    DEFAULT_MODEL = "claude-3-5-haiku-20241022"
    # Average tokens per character for Claude (similar to GPT)
    _CHARS_PER_TOKEN = 4

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
        return "anthropic"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the Anthropic Messages API and return the response text.

        Anthropic separates the system prompt from the messages list,
        so we handle that conversion here.
        """
        model = kwargs.pop("model", self._model)
        max_tokens = kwargs.pop("max_tokens", 1024)
        # Anthropic doesn't use temperature the same way; still accepted
        temperature = kwargs.pop("temperature", 1.0)

        # Extract system message if present (Anthropic uses a top-level param)
        system_prompt: Optional[str] = None
        filtered_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg.get("role") == "system":
                # Concatenate multiple system messages
                system_prompt = (
                    (system_prompt + "\n\n" + msg["content"])
                    if system_prompt
                    else msg["content"]
                )
            else:
                filtered_messages.append({"role": msg["role"], "content": msg["content"]})

        # Anthropic requires at least one human message
        if not filtered_messages:
            raise LLMError("AnthropicProvider requires at least one non-system message.")

        try:
            create_kwargs: dict[str, Any] = dict(
                model=model,
                max_tokens=max_tokens,
                messages=filtered_messages,
                **kwargs,
            )
            if system_prompt:
                create_kwargs["system"] = system_prompt
            # Only pass temperature if it's not the default (Anthropic's extended thinking
            # requires temperature=1, regular calls accept 0-1)
            create_kwargs["temperature"] = temperature

            response = self._client.messages.create(**create_kwargs)
            # Response content is a list of blocks; extract text blocks
            text_parts = [
                block.text
                for block in response.content
                if hasattr(block, "text")
            ]
            return "\n".join(text_parts)
        except Exception as exc:
            raise self._map_error(exc) from exc

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for Claude using a character-based heuristic.

        Anthropic does not expose tiktoken, so we use a ~4 chars/token approximation.
        """
        return max(1, len(text) // self._CHARS_PER_TOKEN)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> str:
        key = (
            (self._config.anthropic_api_key if self._config and hasattr(self._config, "anthropic_api_key") else None)
            or os.environ.get("ANTHROPIC_API_KEY")
            or ""
        )
        if not key:
            raise LLMError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY env var or provide it in config."
            )
        return key

    def _resolve_model(self) -> str:
        return (
            (self._config.anthropic_model if self._config and hasattr(self._config, "anthropic_model") else None)
            or os.environ.get("ANTHROPIC_MODEL")
            or self.DEFAULT_MODEL
        )

    def _build_client(self):
        try:
            import anthropic
            return anthropic.Anthropic(api_key=self._api_key)
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package is required for the Anthropic provider. "
                "Install it with: pip install anthropic"
            ) from exc

    @staticmethod
    def _map_error(exc: Exception) -> LLMError:
        """Map Anthropic SDK exceptions to LLMError."""
        try:
            import anthropic
            if isinstance(exc, anthropic.AuthenticationError):
                return LLMError(f"Anthropic authentication failed: {exc}")
            if isinstance(exc, anthropic.RateLimitError):
                return LLMError(f"Anthropic rate limit exceeded: {exc}")
            if isinstance(exc, anthropic.APIConnectionError):
                return LLMError(f"Anthropic connection error: {exc}")
            if isinstance(exc, anthropic.APIStatusError):
                return LLMError(f"Anthropic API error (status {exc.status_code}): {exc}")
            if isinstance(exc, anthropic.BadRequestError):
                return LLMError(f"Anthropic bad request: {exc}")
        except ImportError:
            pass
        return LLMError(f"Anthropic provider error: {exc}")