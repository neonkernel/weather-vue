"""Ollama local LLM provider implementation."""

from typing import Any

from ...exceptions import LLMError
from ...logger import get_logger
from ..base import BaseLLMProvider

logger = get_logger(__name__)

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3"


def _count_tokens_heuristic(text: str) -> int:
    """Approximate token count using character-based heuristic (~4 chars/token)."""
    return max(1, len(text) // 4)


class OllamaProvider(BaseLLMProvider):
    """LLM provider that calls a local Ollama instance via its REST API."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialise the Ollama provider.

        Args:
            host: Base URL of the Ollama server (defaults to DEFAULT_HOST).
            model: Model name to use (defaults to DEFAULT_MODEL).
            **kwargs: Extra keyword arguments (ignored).
        """
        try:
            import requests as _requests
        except ImportError as exc:
            raise LLMError(
                "requests package is not installed. Run: pip install requests"
            ) from exc

        self._requests = _requests
        self._host = (host or DEFAULT_HOST).rstrip("/")
        self._model = model or DEFAULT_MODEL
        logger.debug(
            "OllamaProvider initialised with host=%s, model=%s",
            self._host,
            self._model,
        )

    def get_default_model(self) -> str:
        return DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        """Use character-based heuristic (no token counter available locally)."""
        return _count_tokens_heuristic(text)

    def list_models(self) -> list[str]:
        """
        Query the Ollama server for available models.

        Returns:
            A list of model name strings.

        Raises:
            LLMError: If the server is unreachable or returns an error.
        """
        url = f"{self._host}/api/tags"
        try:
            response = self._requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except self._requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Is the server running?"
            ) from exc
        except self._requests.exceptions.HTTPError as exc:
            raise LLMError(f"Ollama list-models HTTP error: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Ollama list-models unexpected error: {exc}") from exc

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the Ollama /api/chat endpoint with OpenAI-compatible message format.

        Args:
            messages: Conversation messages with 'role' and 'content'.
            **kwargs: Overrides for model, temperature, etc.

        Returns:
            The assistant's reply text.

        Raises:
            LLMError: On connection errors, HTTP errors, or malformed responses.
        """
        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", 0.3)
        # Ollama uses 'options' sub-dict for sampling parameters
        options: dict[str, Any] = {"temperature": temperature}
        if "max_tokens" in kwargs:
            options["num_predict"] = kwargs.pop("max_tokens")

        url = f"{self._host}/api/chat"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        logger.debug(
            "Ollama completion request: model=%s, messages=%d", model, len(messages)
        )

        try:
            response = self._requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
        except self._requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Is the server running?"
            ) from exc
        except self._requests.exceptions.Timeout as exc:
            raise LLMError(
                f"Ollama request timed out after 120 s for model '{model}'."
            ) from exc
        except self._requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            body = exc.response.text if exc.response is not None else ""
            raise LLMError(
                f"Ollama HTTP {status} error: {body or exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError(
                f"Ollama returned non-JSON response: {response.text[:200]}"
            ) from exc

        # Ollama /api/chat (non-streaming) returns:
        # {"model": ..., "message": {"role": "assistant", "content": "..."}, ...}
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError(
                f"Unexpected Ollama response structure: {data}"
            ) from exc

        if not content:
            raise LLMError("Ollama returned an empty response.")

        logger.debug(
            "Ollama completion succeeded, eval_count=%s", data.get("eval_count")
        )
        return content