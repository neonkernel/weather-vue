"""Anthropic Claude provider implementation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from summarizer.exceptions import LLMError
from summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from summarizer.config import SummarizerConfig

DEFAULT_MODEL = "claude-3-5-haiku-20241022"
# Rough character-to-token ratio for Claude models
CHARS_PER_TOKEN = 4

# Mapping of friendly model aliases to canonical Claude model IDs
MODEL_ALIASES: dict[str, str] = {
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
    "claude-sonnet-4": "claude-sonnet-4-5",
}


class AnthropicProvider(BaseLLMProvider):
    """
    LLM provider backed by Anthropic's Claude models.

    Handles the message format differences between the OpenAI-style
    messages list (with optional 'system' role) and Anthropic's API
    which separates system prompts from the messages array.
    """

    def __init__(self, config: "SummarizerConfig") -> None:
        self._config = config
        api_key = (
            getattr(config, "anthropic_api_key", None)
            or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        if not api_key:
            raise LLMError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment "
                "variable or anthropic_api_key in config."
            )

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
        except ImportError as exc:
            raise LLMError(
                "anthropic package is not installed. Run: pip install anthropic"
            ) from exc

        raw_model = (
            getattr(config, "model", None)
            or os.environ.get("DEFAULT_MODEL", DEFAULT_MODEL)
        )
        self._model = MODEL_ALIASES.get(raw_model, raw_model)

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send messages to Anthropic Claude and return the assistant reply.

        Extracts any 'system' role message and passes it as the dedicated
        system parameter; the remaining messages are forwarded as-is.
        """
        raw_model = kwargs.pop("model", self._model)
        model = MODEL_ALIASES.get(raw_model, raw_model)
        max_tokens = kwargs.pop(
            "max_tokens", getattr(self._config, "max_tokens", 4096)
        )

        # Separate system message from conversation messages
        system_parts: list[str] = []
        conversation: list[dict[str, str]] = []
        for msg in messages:
            if msg.get("role") == "system":
                system_parts.append(msg["content"])
            else:
                conversation.append({"role": msg["role"], "content": msg["content"]})

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        try:
            create_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": conversation,
                **kwargs,
            }
            if system_prompt:
                create_kwargs["system"] = system_prompt

            response = self._client.messages.create(**create_kwargs)
            # Extract text from the first content block
            content = response.content
            if not content:
                return ""
            block = content[0]
            return getattr(block, "text", str(block))
        except Exception as exc:
            raise LLMError(f"Anthropic completion failed: {exc}") from exc

    def get_default_model(self) -> str:
        return self._model or DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        """Character-based heuristic: ~4 characters per token for Claude."""
        return max(1, len(text) // CHARS_PER_TOKEN)

    def get_provider_name(self) -> str:
        return "anthropic"