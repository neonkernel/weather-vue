"""OpenAI LLM provider implementation."""

from typing import Any

from ...exceptions import LLMError
from ...logger import get_logger
from ..base import BaseLLMProvider

logger = get_logger(__name__)

# Default models
DEFAULT_MODEL = "gpt-4o-mini"
FALLBACK_MODEL = "gpt-3.5-turbo"

# Token counting: try tiktoken, fall back to heuristic
try:
    import tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available; token counting will use character heuristic")


def _count_tokens_tiktoken(text: str, model: str) -> int:
    """Count tokens using tiktoken for accurate OpenAI token counts."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def _count_tokens_heuristic(text: str) -> int:
    """Approximate token count using character-based heuristic (~4 chars/token)."""
    return max(1, len(text) // 4)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider that calls the OpenAI Chat Completions API."""

    def __init__(self, api_key: str, model: str | None = None, **kwargs: Any) -> None:
        """
        Initialise the OpenAI provider.

        Args:
            api_key: OpenAI API key.
            model: Model to use (defaults to DEFAULT_MODEL).
            **kwargs: Extra keyword arguments (ignored).
        """
        try:
            from openai import OpenAI, AuthenticationError, RateLimitError, APIError
        except ImportError as exc:
            raise LLMError(
                "openai package is not installed. Run: pip install openai"
            ) from exc

        self._openai_module = __import__("openai")
        self._client = OpenAI(api_key=api_key)
        self._model = model or DEFAULT_MODEL
        logger.debug("OpenAIProvider initialised with model=%s", self._model)

    def get_default_model(self) -> str:
        return DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        if _TIKTOKEN_AVAILABLE:
            return _count_tokens_tiktoken(text, self._model)
        return _count_tokens_heuristic(text)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the OpenAI Chat Completions endpoint.

        Args:
            messages: Conversation messages with 'role' and 'content'.
            **kwargs: Overrides for model, temperature, max_tokens, etc.

        Returns:
            The assistant's reply text.

        Raises:
            LLMError: Wraps any OpenAI SDK errors.
        """
        import openai

        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", 0.3)
        max_tokens = kwargs.pop("max_tokens", 4096)

        logger.debug(
            "OpenAI completion request: model=%s, messages=%d", model, len(messages)
        )

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMError("OpenAI returned an empty response.")
            logger.debug("OpenAI completion succeeded, tokens used=%s", response.usage)
            return content

        except openai.AuthenticationError as exc:
            raise LLMError(f"OpenAI authentication failed: {exc}") from exc
        except openai.RateLimitError as exc:
            raise LLMError(f"OpenAI rate limit exceeded: {exc}") from exc
        except openai.BadRequestError as exc:
            raise LLMError(f"OpenAI bad request: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise LLMError(f"OpenAI connection error: {exc}") from exc
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc