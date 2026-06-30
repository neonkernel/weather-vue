"""Ollama local LLM provider."""

from __future__ import annotations

import json
import logging
from typing import Any

from ...exceptions import LLMError
from ..base import BaseLLMProvider

logger = logging.getLogger(__name__)

_DEFAULT_HOST = "http://localhost:11434"
_DEFAULT_MODEL = "llama3"
_CHARS_PER_TOKEN = 4  # Conservative character-based heuristic


class OllamaProvider(BaseLLMProvider):
    """LLM provider that calls a local Ollama instance via its REST API."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> None:
        try:
            import requests  # type: ignore  # noqa: F401
        except ImportError as exc:
            raise LLMError(
                "The 'requests' package is required for OllamaProvider. "
                "Install it with: pip install requests"
            ) from exc

        self._host = (host or _DEFAULT_HOST).rstrip("/")
        self._model = model or _DEFAULT_MODEL
        self._temperature = temperature
        self._max_tokens = max_tokens

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return _DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        import requests  # type: ignore

        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", self._temperature)
        # Ollama uses 'num_predict' for max new tokens
        num_predict = kwargs.pop("max_tokens", self._max_tokens)

        logger.debug(
            "Ollama request | host=%s model=%s temperature=%s num_predict=%s messages=%d",
            self._host,
            model,
            temperature,
            num_predict,
            len(messages),
        )

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        payload.update(kwargs)

        url = f"{self._host}/api/chat"

        try:
            response = requests.post(url, json=payload, timeout=120)
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Could not connect to Ollama at {self._host}. "
                "Make sure the Ollama service is running."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise LLMError(
                f"Request to Ollama timed out after 120 seconds: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LLMError(f"Ollama request error: {exc}") from exc

        if response.status_code == 404:
            raise LLMError(
                f"Ollama model '{model}' not found. "
                f"Pull it first with: ollama pull {model}"
            )
        if response.status_code == 401:
            raise LLMError("Ollama returned 401 Unauthorized.")
        if not response.ok:
            raise LLMError(
                f"Ollama returned HTTP {response.status_code}: {response.text[:500]}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise LLMError(
                f"Could not parse Ollama response as JSON: {response.text[:200]}"
            ) from exc

        # /api/chat response shape: {"message": {"role": "assistant", "content": "..."}}
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError(
                f"Unexpected Ollama response structure: {data}"
            ) from exc

        if not isinstance(content, str):
            raise LLMError(
                f"Ollama response content is not a string: {type(content)}"
            )

        return content

    # ------------------------------------------------------------------
    # Extra utility methods
    # ------------------------------------------------------------------

    def list_models(self) -> list[str]:
        """Return a list of locally available Ollama model names."""
        import requests  # type: ignore

        url = f"{self._host}/api/tags"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except requests.exceptions.RequestException as exc:
            raise LLMError(f"Failed to list Ollama models: {exc}") from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError(f"Unexpected response from Ollama /api/tags: {exc}") from exc