"""Anthropic Claude LLM provider implementation."""

import os
from typing import Any

try:
    import anthropic as anthropic_sdk
    from anthropic import Anthropic, APIError, AuthenticationError, RateLimitError, APIConnectionError
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from ..base import BaseLLMProvider
from ...exceptions import LLMError


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider using the official anthropic SDK."""

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    # Approximate characters per token for Claude models
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Claude model name. Falls back to DEFAULT_MODEL.
            **kwargs: Additional options (currently unused).
        """
        if not HAS_ANTHROPIC:
            raise LLMError(
                "anthropic package is not installed. Run: pip install anthropic"
            )

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise LLMError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable or pass api_key."
            )

        self._model = model or self.DEFAULT_MODEL
        self._client = Anthropic(api_key=resolved_key)

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send messages to Anthropic Claude and return the assistant response text.

        Anthropic's API separates the system prompt from the conversation messages,
        so we extract any 'system' role messages before sending.
        """
        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", 0.3)
        max_tokens = kwargs.pop("max_tokens", 1024)

        # Anthropic treats system messages separately
        system_parts: list[str] = []
        conversation: list[dict[str, str]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                conversation.append({"role": role, "content": content})

        system_prompt = "\n\n".join(system_parts) if system_parts else anthropic_sdk.NOT_GIVEN

        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,  # type: ignore[arg-type]
                messages=conversation,  # type: ignore[arg-type]
                **kwargs,
            )

            # Extract text from the first content block
            if not response.content:
                raise LLMError("Anthropic returned an empty response.")

            text_blocks = [
                block.text
                for block in response.content
                if hasattr(block, "text")
            ]
            if not text_blocks:
                raise LLMError("Anthropic response contained no text blocks.")

            return "\n".join(text_blocks)

        except AuthenticationError as exc:
            raise LLMError(f"Anthropic authentication failed: {exc}") from exc
        except RateLimitError as exc:
            raise LLMError(f"Anthropic rate limit exceeded: {exc}") from exc
        except APIConnectionError as exc:
            raise LLMError(f"Anthropic connection error: {exc}") from exc
        except APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Unexpected error from Anthropic provider: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """Estimate token count using a character-based heuristic for Claude models."""
        return max(1, len(text) // self.CHARS_PER_TOKEN)