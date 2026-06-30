"""Anthropic Claude LLM provider implementation."""

from typing import Any

from ...exceptions import LLMError
from ...logger import get_logger
from ..base import BaseLLMProvider

logger = get_logger(__name__)

try:
    import anthropic as anthropic_sdk
    from anthropic import (
        Anthropic,
        APIError,
        AuthenticationError,
        RateLimitError,
        BadRequestError,
    )
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider using the official anthropic SDK."""

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.3

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
    ) -> None:
        if not _ANTHROPIC_AVAILABLE:
            raise LLMError(
                "anthropic package is not installed. Run: pip install anthropic"
            )

        if not api_key:
            raise LLMError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY or pass api_key."
            )

        self._model = model or self.DEFAULT_MODEL
        self._client = Anthropic(api_key=api_key)
        logger.debug("AnthropicProvider initialized with model=%s", self._model)

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _split_messages(
        self, messages: list[dict[str, str]]
    ) -> tuple[str | None, list[dict[str, str]]]:
        """
        Anthropic's API separates the system prompt from conversation messages.
        Extract any leading 'system' role message and return it separately.
        """
        system_prompt: str | None = None
        conversation: list[dict[str, str]] = []

        for msg in messages:
            if msg["role"] == "system" and system_prompt is None and not conversation:
                system_prompt = msg["content"]
            else:
                conversation.append(msg)

        return system_prompt, conversation

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Call the Anthropic Messages API."""
        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        model = kwargs.get("model", self._model)

        system_prompt, conversation = self._split_messages(messages)

        if not conversation:
            raise LLMError("At least one non-system message is required.")

        logger.debug(
            "Anthropic request: model=%s, messages=%d, max_tokens=%d",
            model,
            len(conversation),
            max_tokens,
        )

        try:
            kwargs_api: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": conversation,  # type: ignore[arg-type]
            }
            if system_prompt:
                kwargs_api["system"] = system_prompt

            response = self._client.messages.create(**kwargs_api)

            # Extract text from the response content blocks
            content_parts: list[str] = []
            for block in response.content:
                if hasattr(block, "text"):
                    content_parts.append(block.text)

            result = "".join(content_parts)
            logger.debug(
                "Anthropic response received, length=%d chars", len(result)
            )
            return result

        except AuthenticationError as exc:
            raise LLMError(f"Anthropic authentication failed: {exc}") from exc
        except RateLimitError as exc:
            raise LLMError(f"Anthropic rate limit exceeded: {exc}") from exc
        except BadRequestError as exc:
            raise LLMError(f"Anthropic bad request: {exc}") from exc
        except APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling Anthropic: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """
        Anthropic doesn't expose tiktoken-style counting publicly.
        Use a character-based heuristic: ~3.5 chars per token for Claude models.
        """
        return max(1, int(len(text) / 3.5))