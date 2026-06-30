"""Anthropic Claude LLM provider."""

from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from src.summarizer.config import Config


class AnthropicProvider(BaseLLMProvider):
    """LLM provider backed by the Anthropic Claude API."""

    DEFAULT_MODEL = "claude-3-5-haiku-20241022"

    # Mapping from short aliases to full model IDs
    MODEL_ALIASES: dict[str, str] = {
        "claude-3-5-haiku": "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3-opus": "claude-3-opus-20240229",
        "claude-3-haiku": "claude-3-haiku-20240307",
        "claude-3-sonnet": "claude-3-sonnet-20240229",
    }

    def __init__(self, config: "Config | None" = None) -> None:
        self._config = config
        api_key = (
            (config.anthropic_api_key if config and hasattr(config, "anthropic_api_key") else None)
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        if not api_key:
            raise LLMError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or provide it in the config."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package is required for the Anthropic provider. "
                "Install it with: pip install anthropic"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        raw_model = (
            (config.model if config and hasattr(config, "model") and config.model else None)
            or os.environ.get("DEFAULT_MODEL")
            or self.DEFAULT_MODEL
        )
        self._model = self.MODEL_ALIASES.get(raw_model, raw_model)

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        """Character-based heuristic: ~3.5 chars per Claude token."""
        return max(1, round(len(text) / 3.5))

    def _split_system_and_user(
        self, messages: list[dict[str, str]]
    ) -> tuple[str | None, list[dict[str, str]]]:
        """
        Anthropic's API separates the system prompt from the conversation.

        Returns:
            (system_prompt, remaining_messages)
        """
        system_prompt: str | None = None
        conversation: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                conversation.append({"role": msg["role"], "content": msg["content"]})
        return system_prompt, conversation

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send a message to the Anthropic Claude API."""
        model = kwargs.pop("model", self._model)
        max_tokens = kwargs.pop("max_tokens", None)
        if max_tokens is None:
            if self._config and hasattr(self._config, "max_tokens") and self._config.max_tokens:
                max_tokens = self._config.max_tokens
            else:
                max_tokens = 4096
        temperature = kwargs.pop("temperature", 0.3)

        system_prompt, conversation = self._split_system_and_user(messages)

        if not conversation:
            raise LLMError("No user/assistant messages provided to AnthropicProvider.")

        try:
            request_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": conversation,
                "temperature": temperature,
                **kwargs,
            }
            if system_prompt:
                request_kwargs["system"] = system_prompt

            response = self._client.messages.create(**request_kwargs)
            # response.content is a list of content blocks
            text_blocks = [block.text for block in response.content if hasattr(block, "text")]
            if not text_blocks:
                raise LLMError("Anthropic returned an empty response.")
            return "".join(text_blocks)
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc