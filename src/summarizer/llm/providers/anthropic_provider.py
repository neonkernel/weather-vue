"""Anthropic Claude provider implementation."""
from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from src.summarizer.config import Config

_DEFAULT_MODEL = "claude-3-5-haiku-20241022"
_CHARS_PER_TOKEN = 4  # Conservative character-based heuristic

# Mapping of user-friendly short names → full Anthropic model IDs
_MODEL_ALIASES: dict[str, str] = {
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
    "claude-opus-4": "claude-opus-4-0",
    "claude-sonnet-4": "claude-sonnet-4-0",
}


def _resolve_model(model: str) -> str:
    """Expand short model aliases to full model IDs."""
    return _MODEL_ALIASES.get(model, model)


class AnthropicProvider(BaseLLMProvider):
    """LLM provider backed by the Anthropic Claude API."""

    def __init__(self, config: "Config") -> None:
        self._config = config
        raw_model = getattr(config, "model", None) or _DEFAULT_MODEL
        self._model = _resolve_model(raw_model)

        api_key = (
            getattr(config, "anthropic_api_key", None)
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        if not api_key:
            raise LLMError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or provide anthropic_api_key in config."
            )

        try:
            import anthropic as _anthropic
            self._client = _anthropic.Anthropic(api_key=api_key)
            self._anthropic = _anthropic
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package is required for the Anthropic provider. "
                "Install it with: pip install anthropic"
            ) from exc

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    @property
    def default_model(self) -> str:
        return _DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def count_tokens(self, text: str) -> int:
        """Character-based token heuristic (Anthropic doesn't expose a free counter)."""
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the Anthropic Messages API.

        The OpenAI-style 'system' role is extracted and passed as Anthropic's
        top-level system parameter; remaining messages are forwarded as-is.

        Args:
            messages: List of {'role': ..., 'content': ...} dicts.
            **kwargs: Overrides for model, temperature, max_tokens.

        Returns:
            Assistant message content string.

        Raises:
            LLMError: Wraps any anthropic SDK exception.
        """
        model = _resolve_model(kwargs.pop("model", None) or self._model)
        temperature = kwargs.pop(
            "temperature",
            getattr(self._config, "temperature", 0.3),
        )
        max_tokens = kwargs.pop(
            "max_tokens",
            getattr(self._config, "max_tokens", 4096),
        )

        # Anthropic separates system messages from the conversation
        system_parts: list[str] = []
        conversation: list[dict[str, str]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                conversation.append({"role": role, "content": content})

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        try:
            create_kwargs: dict[str, Any] = {
                "model": model,
                "messages": conversation,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            }
            if system_prompt:
                create_kwargs["system"] = system_prompt

            response = self._client.messages.create(**create_kwargs)

            # Extract text from the first content block
            content_blocks = response.content
            if not content_blocks:
                raise LLMError("Anthropic returned an empty response.")

            text_parts = [
                block.text
                for block in content_blocks
                if hasattr(block, "text")
            ]
            if not text_parts:
                raise LLMError("Anthropic response contained no text blocks.")

            return "".join(text_parts)

        except self._anthropic.AuthenticationError as exc:
            raise LLMError(f"Anthropic authentication failed: {exc}") from exc
        except self._anthropic.RateLimitError as exc:
            raise LLMError(f"Anthropic rate limit exceeded: {exc}") from exc
        except self._anthropic.BadRequestError as exc:
            raise LLMError(f"Anthropic bad request: {exc}") from exc
        except self._anthropic.APIConnectionError as exc:
            raise LLMError(f"Anthropic connection error: {exc}") from exc
        except self._anthropic.APIStatusError as exc:
            raise LLMError(
                f"Anthropic API error ({exc.status_code}): {exc.message}"
            ) from exc
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Unexpected Anthropic error: {exc}") from exc