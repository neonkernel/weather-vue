"""Anthropic Claude LLM provider implementation."""

from typing import Any

from ...exceptions import LLMError
from ...logger import get_logger
from ..base import BaseLLMProvider

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-3-5-haiku-20241022"

# Map short aliases to full Anthropic model IDs
MODEL_ALIASES: dict[str, str] = {
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
}


def _resolve_model(model: str) -> str:
    """Resolve a short alias or return the model string as-is."""
    return MODEL_ALIASES.get(model, model)


def _count_tokens_heuristic(text: str) -> int:
    """Approximate token count using character-based heuristic (~4 chars/token)."""
    return max(1, len(text) // 4)


class AnthropicProvider(BaseLLMProvider):
    """LLM provider that uses the Anthropic Python SDK to call Claude models."""

    def __init__(self, api_key: str, model: str | None = None, **kwargs: Any) -> None:
        """
        Initialise the Anthropic provider.

        Args:
            api_key: Anthropic API key.
            model: Model name or alias (defaults to DEFAULT_MODEL).
            **kwargs: Extra keyword arguments (ignored).
        """
        try:
            import anthropic as anthropic_sdk
        except ImportError as exc:
            raise LLMError(
                "anthropic package is not installed. Run: pip install anthropic"
            ) from exc

        self._anthropic = anthropic_sdk
        self._client = anthropic_sdk.Anthropic(api_key=api_key)
        self._model = _resolve_model(model or DEFAULT_MODEL)
        logger.debug("AnthropicProvider initialised with model=%s", self._model)

    def get_default_model(self) -> str:
        return DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        """Use character-based heuristic (Anthropic doesn't expose a public token counter)."""
        return _count_tokens_heuristic(text)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the Anthropic Messages API.

        The Anthropic API separates the system prompt from the conversation turns.
        This method extracts any leading 'system' role messages and passes them
        via the dedicated `system` parameter.

        Args:
            messages: Conversation messages with 'role' and 'content'.
            **kwargs: Overrides for model, temperature, max_tokens, etc.

        Returns:
            The assistant's reply text.

        Raises:
            LLMError: Wraps any Anthropic SDK errors.
        """
        model = _resolve_model(kwargs.pop("model", self._model))
        temperature = kwargs.pop("temperature", 0.3)
        max_tokens = kwargs.pop("max_tokens", 4096)

        # Anthropic treats the system prompt separately
        system_parts: list[str] = []
        conversation: list[dict[str, str]] = []

        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                conversation.append({"role": msg["role"], "content": msg["content"]})

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        logger.debug(
            "Anthropic completion request: model=%s, conversation_turns=%d",
            model,
            len(conversation),
        )

        try:
            create_kwargs: dict[str, Any] = dict(
                model=model,
                messages=conversation,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            if system_prompt:
                create_kwargs["system"] = system_prompt

            response = self._client.messages.create(**create_kwargs)

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

            result = "".join(text_blocks)
            logger.debug(
                "Anthropic completion succeeded, stop_reason=%s", response.stop_reason
            )
            return result

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