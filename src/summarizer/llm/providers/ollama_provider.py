"""Ollama provider — calls the local Ollama REST API over HTTP."""
from __future__ import annotations

import json
import os
from typing import Any, TYPE_CHECKING

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from src.summarizer.config import Config

_DEFAULT_MODEL = "llama3.2"
_DEFAULT_HOST = "http://localhost:11434"
_CHARS_PER_TOKEN = 4  # Conservative heuristic


class OllamaProvider(BaseLLMProvider):
    """LLM provider backed by a local Ollama instance."""

    def __init__(self, config: "Config") -> None:
        self._config = config
        self._model = getattr(config, "model", None) or _DEFAULT_MODEL
        self._host = (
            getattr(config, "ollama_host", None)
            or os.environ.get("OLLAMA_HOST", _DEFAULT_HOST)
        ).rstrip("/")

        try:
            import requests as _requests
            self._requests = _requests
        except ImportError as exc:
            raise LLMError(
                "The 'requests' package is required for the Ollama provider. "
                "Install it with: pip install requests"
            ) from exc

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    @property
    def default_model(self) -> str:
        return _DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "ollama"

    def count_tokens(self, text: str) -> int:
        """Character-based token heuristic."""
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the Ollama /api/chat endpoint.

        Args:
            messages: List of {'role': ..., 'content': ...} dicts.
            **kwargs: Overrides for model, temperature, max_tokens.

        Returns:
            Assistant message content string.

        Raises:
            LLMError: On HTTP errors, connection failures, or malformed responses.
        """
        model = kwargs.pop("model", None) or self._model
        temperature = kwargs.pop(
            "temperature",
            getattr(self._config, "temperature", 0.3),
        )
        max_tokens = kwargs.pop(
            "max_tokens",
            getattr(self._config, "max_tokens", 4096),
        )

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs,
            },
        }

        url = f"{self._host}/api/chat"

        try:
            response = self._requests.post(
                url,
                json=payload,
                timeout=120,
            )
        except self._requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Make sure Ollama is running: https://ollama.ai"
            ) from exc
        except self._requests.exceptions.Timeout as exc:
            raise LLMError(
                f"Ollama request timed out after 120 seconds (model: {model})."
            ) from exc
        except self._requests.exceptions.RequestException as exc:
            raise LLMError(f"Ollama request error: {exc}") from exc

        self._raise_for_status(response, model)

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMError(
                f"Ollama returned non-JSON response: {response.text[:200]}"
            ) from exc

        # Ollama /api/chat response shape:
        # {"message": {"role": "assistant", "content": "..."}, ...}
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError(
                f"Unexpected Ollama response structure: {data}"
            ) from exc

        if not content:
            raise LLMError("Ollama returned an empty response.")

        return content

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _raise_for_status(self, response: Any, model: str) -> None:
        """Convert HTTP error codes to LLMError."""
        status = response.status_code
        if status == 200:
            return
        if status == 404:
            raise LLMError(
                f"Ollama model '{model}' not found. "
                f"Pull it first with: ollama pull {model}"
            )
        if status == 400:
            try:
                detail = response.json().get("error", response.text)
            except Exception:
                detail = response.text
            raise LLMError(f"Ollama bad request: {detail}")
        if status == 500:
            raise LLMError(f"Ollama internal server error: {response.text[:300]}")
        raise LLMError(
            f"Ollama returned HTTP {status}: {response.text[:300]}"
        )

    def list_models(self) -> list[str]:
        """
        Query Ollama for available local models.

        Returns:
            List of model name strings.

        Raises:
            LLMError: On connection or API errors.
        """
        url = f"{self._host}/api/tags"
        try:
            response = self._requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except self._requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}."
            ) from exc
        except Exception as exc:
            raise LLMError(f"Failed to list Ollama models: {exc}") from exc