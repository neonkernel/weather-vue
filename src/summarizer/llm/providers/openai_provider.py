"""OpenAI LLM provider implementation."""

from typing import Any

from ...exceptions import LLMError
from ...logger import get_logger
from ..base import BaseLLMProvider

logger = get_logger(__name__)

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False

try:
    from openai import OpenAI, APIError, AuthenticationError, RateLimitError
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider conforming to BaseLLMProvider."""

    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.3

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
    ) -> None:
        if not _OPENAI_AVAILABLE:
            raise LLMError(
                "openai package is not installed. Run: pip install openai"
            )

        if not api_key:
            raise LLMError(
                "OpenAI API key is required. Set OPENAI_API_KEY or pass api_key."
            )

        self._model = model or self.DEFAULT_MODEL
        self._client = OpenAI(api_key=api_key)
        logger.debug("OpenAIProvider initialized with model=%s", self._model)

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Call the OpenAI chat completions API."""
        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        model = kwargs.get("model", self._model)

        logger.debug(
            "OpenAI request: model=%s, messages=%d, max_tokens=%d",
            model,
            len(messages),
            max_tokens,
        )

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""
            logger.debug(
                "OpenAI response received, length=%d chars", len(content)
            )
            return content

        except AuthenticationError as exc:
            raise LLMError(f"OpenAI authentication failed: {exc}") from exc
        except RateLimitError as exc:
            raise LLMError(f"OpenAI rate limit exceeded: {exc}") from exc
        except APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling OpenAI: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """Use tiktoken for accurate token counting when available."""
        if _TIKTOKEN_AVAILABLE:
            try:
                encoding = tiktoken.encoding_for_model(self._model)
                return len(encoding.encode(text))
            except KeyError:
                # Fall back to cl100k_base for unknown models
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
        # Fallback heuristic: ~4 chars per token
        return max(1, len(text) // 4)