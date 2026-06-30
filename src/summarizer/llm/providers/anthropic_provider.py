"""Anthropic Claude LLM provider implementation."""

from typing import Any

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider
from src.summarizer.logger import get_logger

logger = get_logger(__name__)

# Characters-per-token heuristic for Claude models
_CHARS_PER_TOKEN = 4


class AnthropicProvider(BaseLLMProvider):
    """LLM provider backed by the Anthropic Claude API."""

    DEFAULT_MODEL = "claude-3-5-haiku-20241022"
    MAX_TOKENS_DEFAULT = 4096

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        max_tokens: int = MAX_TOKENS_DEFAULT,
        temperature: float = 0.3,
    ) -> None:
        if not api_key:
            raise LLMError("Anthropic API key is required.")

        try:
            import anthropic
            self._anthropic = anthropic
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package is not installed. "
                "Run: pip install anthropic"
            ) from exc

        self._client = self._anthropic.Anthropic(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens
        self._temperature = temperature

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def _split_messages(
        self, messages: list[dict[str, str]]
    ) -> tuple[str | None, list[dict[str, str]]]:
        """
        Anthropic's API separates the system prompt from conversation messages.
        Extract the first system message (if any) and return non-system messages.
        """
        system_prompt: str | None = None
        conversation: list[dict[str, str]] = []

        for msg in messages:
            if msg["role"] == "system":
                # Anthropic only supports a single top-level system prompt;
                # concatenate multiple system messages if present.
                if system_prompt is None:
                    system_prompt = msg["content"]
                else:
                    system_prompt += "\n" + msg["content"]
            else:
                conversation.append({"role": msg["role"], "content": msg["content"]})

        return system_prompt, conversation

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Call the Anthropic Messages API."""
        model = kwargs.get("model", self._model)
        max_tokens = kwargs.get("max_tokens", self._max_tokens)
        temperature = kwargs.get("temperature", self._temperature)

        system_prompt, conversation = self._split_messages(messages)

        if not conversation:
            raise LLMError("No user/assistant messages provided to AnthropicProvider.")

        logger.debug(
            "AnthropicProvider.complete: model=%s, messages=%d",
            model,
            len(conversation),
        )

        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conversation,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt

        try:
            response = self._client.messages.create(**create_kwargs)
            # response.content is a list of ContentBlock objects
            text_blocks = [
                block.text
                for block in response.content
                if hasattr(block, "text")
            ]
            if not text_blocks:
                raise LLMError("Anthropic returned an empty response.")
            return "".join(text_blocks).strip()

        except self._anthropic.AuthenticationError as exc:
            raise LLMError(f"Anthropic authentication failed: {exc}") from exc
        except self._anthropic.RateLimitError as exc:
            raise LLMError(f"Anthropic rate limit exceeded: {exc}") from exc
        except self._anthropic.APIStatusError as exc:
            raise LLMError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
        except self._anthropic.APIConnectionError as exc:
            raise LLMError(f"Anthropic connection error: {exc}") from exc
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Unexpected error calling Anthropic: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """Character-based heuristic token count (~4 chars per token for Claude)."""
        return max(1, len(text) // _CHARS_PER_TOKEN)