"""Ollama provider implementation using direct HTTP calls to the local REST API."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from summarizer.exceptions import LLMError
from summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from summarizer.config import SummarizerConfig

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"
# Rough character-to-token ratio for open-source models
CHARS_PER_TOKEN = 4


class OllamaProvider(BaseLLMProvider):
    """
    LLM provider backed by a local Ollama instance.

    Communicates with the Ollama REST API via the `requests` library.
    Supports the /api/chat endpoint for multi-turn conversations and
    /api/tags for listing available models.
    """

    def __init__(self, config: "SummarizerConfig") -> None:
        self._config = config
        self._host = (
            getattr(config, "ollama_host", None)
            or os.environ.get("OLLAMA_HOST", DEFAULT_HOST)
        ).rstrip("/")

        self._model = (
            getattr(config, "model", None)
            or os.environ.get("DEFAULT_MODEL", DEFAULT_MODEL)
        )

        try:
            import requests
            self._requests = requests
        except ImportError as exc:
            raise LLMError(
                "requests package is not installed. Run: pip install requests"
            ) from exc

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send messages to Ollama's /api/chat endpoint and return the reply.

        Args:
            messages: Standard messages list with 'role'/'content' dicts.
            **kwargs: Supports 'model', 'temperature', 'stream' overrides.

        Returns:
            The assistant's reply text.

        Raises:
            LLMError: On connection errors, HTTP errors, or unexpected responses.
        """
        model = kwargs.pop("model", self._model)
        stream = kwargs.pop("stream", False)

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }

        url = f"{self._host}/api/chat"

        try:
            response = self._requests.post(
                url,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
        except self._requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Make sure Ollama is running (ollama serve)."
            ) from exc
        except self._requests.exceptions.Timeout as exc:
            raise LLMError(
                f"Request to Ollama timed out after 120s. "
                "Consider using a smaller model or increasing timeout."
            ) from exc
        except self._requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            raise LLMError(
                f"Ollama returned HTTP {status}: {exc}"
            ) from exc
        except Exception as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc

        return self._parse_response(response.text)

    def get_default_model(self) -> str:
        return self._model or DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        """Character-based heuristic: ~4 characters per token."""
        return max(1, len(text) // CHARS_PER_TOKEN)

    def get_provider_name(self) -> str:
        return "ollama"

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def list_models(self) -> list[str]:
        """
        Query the Ollama instance for available models.

        Returns:
            A list of model name strings (e.g. ['llama3.2', 'mistral']).

        Raises:
            LLMError: If the request fails or Ollama is unreachable.
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, raw: str) -> str:
        """
        Parse the Ollama /api/chat response body.

        Ollama may return either:
          - A single JSON object (stream=False)
          - Multiple newline-delimited JSON objects (stream=True)
        """
        raw = raw.strip()
        if not raw:
            return ""

        # Try single JSON object first
        try:
            data = json.loads(raw)
            return self._extract_content(data)
        except json.JSONDecodeError:
            pass

        # Fall back to NDJSON (streaming) format
        parts: list[str] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                parts.append(self._extract_content(obj))
            except json.JSONDecodeError:
                continue
        return "".join(parts)

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        """Extract the assistant message text from a parsed Ollama response."""
        # /api/chat response shape: {"message": {"role": "assistant", "content": "..."}}
        message = data.get("message", {})
        if isinstance(message, dict):
            return message.get("content", "")
        # Fallback for older /api/generate shape
        return data.get("response", "")