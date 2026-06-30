"""Anthropic Claude LLM provider."""

from __future__ import annotations

import logging
from typing import Any

from ...exceptions import LLMError
from ..base import BaseLLMProvider

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
_CHARS_PER_TOKEN = 4  # Conservative heuristic for Claude


class AnthropicProvider(BaseLLMProvider):
    """LLM provider backed by the Anthropic Messages API."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package is required for AnthropicProvider. "
                "Install it with: pip install anthropic"
            ) from exc

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or _DEFAULT_MODEL
        self._temperature = temperature
        self._max_tokens = max_tokens

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return _DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        # Character-based heuristic — Anthropic does not expose a public
        # standalone tokeniser in the SDK at this time.
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", self._temperature)
        max_tokens = kwargs.pop("max_tokens", self._max_tokens)

        # Anthropic separates the system prompt from the conversation turns.
        system_prompt: str | None = None
        conversation: list[dict[str, str]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                # Concatenate multiple system messages if present
                system_prompt = (
                    content if system_prompt is None else f"{system_prompt}\n{content}"
                )
            else:
                # Map 'user' / 'assistant' directly; unknown roles become 'user'
                mapped_role = role if role in ("user", "assistant") else "user"
                conversation.append({"role": mapped_role, "content": content})

        if not conversation:
            raise LLMError(
                "AnthropicProvider requires at least one non-system message."
            )

        logger.debug(
            "Anthropic request | model=%s temperature=%s max_tokens=%s turns=%d",
            model,
            temperature,
            max_tokens,
            len(conversation),
        )

        create_kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            messages=conversation,
            temperature=temperature,
            **kwargs,
        )
        if system_prompt is not None:
            create_kwargs["system"] = system_prompt

        try:
            response = self._client.messages.create(**create_kwargs)
        except self._anthropic.AuthenticationError as exc:
            raise LLMError(f"Anthropic authentication failed: {exc}") from exc
        except self._anthropic.RateLimitError as exc:
            raise LLMError(f"Anthropic rate limit exceeded: {exc}") from exc
        except self._anthropic.BadRequestError as exc:
            raise LLMError(f"Anthropic bad request: {exc}") from exc
        except self._anthropic.APIConnectionError as exc:
            raise LLMError(f"Anthropic connection error: {exc}") from exc
        except self._anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling Anthropic: {exc}") from exc

        # Extract text from the first content block
        if not response.content:
            raise LLMError("Anthropic returned an empty response.")

        first_block = response.content[0]
        if hasattr(first_block, "text"):
            return first_block.text

        raise LLMError(
            f"Unexpected Anthropic response content type: {type(first_block)}"
        )