"""OpenAI LLM provider implementation."""

from typing import Any

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider
from src.summarizer.logger import get_logger

logger = get_logger(__name__)

_TIKTOKEN_AVAILABLE = False
try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    pass


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI API."""

    DEFAULT_MODEL = "gpt-4o-mini"
    FALLBACK_CHARS_PER_TOKEN = 4

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> None:
        if not api_key:
            raise LLMError("OpenAI API key is required.")

        try:
            from openai import OpenAI, APIError, AuthenticationError, RateLimitError
        except ImportError as exc:
            raise LLMError(
                "The 'openai' package is not installed. "
                "Run: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._OpenAI = OpenAI
        self._APIError = APIError
        self._AuthenticationError = AuthenticationError
        self._RateLimitError = RateLimitError

        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._encoding = None

        if _TIKTOKEN_AVAILABLE:
            try:
                self._encoding = tiktoken.encoding_for_model(self._model)
            except KeyError:
                try:
                    self._encoding = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    self._encoding = None

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Call the OpenAI Chat Completions API."""
        model = kwargs.get("model", self._model)
        max_tokens = kwargs.get("max_tokens", self._max_tokens)
        temperature = kwargs.get("temperature", self._temperature)

        logger.debug(
            "OpenAIProvider.complete: model=%s, messages=%d", model, len(messages)
        )

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMError("OpenAI returned an empty response.")
            return content.strip()

        except self._AuthenticationError as exc:
            raise LLMError(f"OpenAI authentication failed: {exc}") from exc
        except self._RateLimitError as exc:
            raise LLMError(f"OpenAI rate limit exceeded: {exc}") from exc
        except self._APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling OpenAI: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken when available, otherwise use heuristic."""
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        # Fallback: ~4 characters per token
        return max(1, len(text) // self.FALLBACK_CHARS_PER_TOKEN)