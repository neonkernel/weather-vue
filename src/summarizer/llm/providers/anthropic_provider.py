"""Anthropic Claude LLM provider implementation."""

import os
from typing import TYPE_CHECKING

from ...exceptions import LLMError
from ..base import BaseLLMProvider

if TYPE_CHECKING:
    from ...config import Config

# Default / available models
DEFAULT_MODEL = "claude-3-5-haiku-20241022"
MODEL_ALIASES = {
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
}


def _resolve_model(model: str) -> str:
    """Expand short alias to full versioned model name if needed."""
    return MODEL_ALIASES.get(model, model)


class AnthropicProvider(BaseLLMProvider):
    """LLM provider backed by the Anthropic Claude API."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.api_key = (
            getattr(config, "anthropic_api_key", None)
            or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        if not self.api_key:
            raise LLMError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or provide anthropic_api_key in config."
            )

        try:
            import anthropic
        except ImportError as exc:
            raise LLMError(
                "anthropic package is not installed. Run: pip install anthropic"
            ) from exc

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def get_default_model(self) -> str:
        model = getattr(self.config, "model", None) or DEFAULT_MODEL
        return _resolve_model(model)

    def complete(self, messages: list, **kwargs) -> str:
        """
        Call the Anthropic Messages API.

        Handles the Anthropic-specific message format:
        - 'system' role messages are extracted and passed as the top-level `system` param.
        - Only 'user' and 'assistant' roles remain in the messages list.

        Args:
            messages: List of {'role': ..., 'content': ...} dicts.
            **kwargs: Overrides for model, max_tokens, temperature.

        Returns:
            The assistant's reply text.

        Raises:
            LLMError: On API errors.
        """
        model = _resolve_model(kwargs.get("model") or self.get_default_model())
        max_tokens = kwargs.get("max_tokens") or getattr(self.config, "max_tokens", 4096)
        temperature = kwargs.get("temperature")
        if temperature is None:
            temperature = getattr(self.config, "temperature", 0.3)

        # Anthropic separates system prompt from conversation messages
        system_parts = []
        conversation = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                conversation.append({"role": role, "content": content})

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        try:
            create_kwargs: dict = dict(
                model=model,
                max_tokens=max_tokens,
                messages=conversation,
                temperature=temperature,
            )
            if system_prompt:
                create_kwargs["system"] = system_prompt

            response = self._client.messages.create(**create_kwargs)
            # Content is a list of blocks; concatenate text blocks
            return "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
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