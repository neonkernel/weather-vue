"""Ollama local LLM provider implementation."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """
    LLM provider that calls a local Ollama instance via its REST API.

    Ollama must be running at the configured host (default: http://localhost:11434).
    No API key is required.
    """

    DEFAULT_MODEL = "llama3.2"
    DEFAULT_HOST = "http://localhost:11434"
    _CHARS_PER_TOKEN = 4  # character-based approximation

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config
        self._host = self._resolve_host().rstrip("/")
        self._model = self._resolve_model()

    # ------------------------------------------------------------------
    # BaseLLMProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the Ollama /api/chat endpoint and return the response text.

        Uses the OpenAI-compatible messages format that Ollama supports.
        """
        model = kwargs.pop("model", self._model)
        # Ollama accepts standard chat options
        options: dict[str, Any] = {}
        if "temperature" in kwargs:
            options["temperature"] = kwargs.pop("temperature")
        if "max_tokens" in kwargs:
            options["num_predict"] = kwargs.pop("max_tokens")

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        payload.update(kwargs)

        url = f"{self._host}/api/chat"
        try:
            import requests
            response = requests.post(
                url,
                json=payload,
                timeout=120,  # local models can be slow
            )
            self._check_http_response(response)
            data = response.json()
            return data.get("message", {}).get("content", "")
        except LLMError:
            raise
        except ImportError as exc:
            raise LLMError(
                "The 'requests' package is required for the Ollama provider. "
                "Install it with: pip install requests"
            ) from exc
        except Exception as exc:
            raise self._map_error(exc) from exc

    def count_tokens(self, text: str) -> int:
        """Estimate token count using a character-based heuristic."""
        return max(1, len(text) // self._CHARS_PER_TOKEN)

    # ------------------------------------------------------------------
    # Ollama-specific helpers
    # ------------------------------------------------------------------

    def list_models(self) -> list[str]:
        """
        Return a list of model names available on the local Ollama instance.

        Raises:
            LLMError: If the Ollama server is unreachable or returns an error.
        """
        url = f"{self._host}/api/tags"
        try:
            import requests
            response = requests.get(url, timeout=10)
            self._check_http_response(response)
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except LLMError:
            raise
        except ImportError as exc:
            raise LLMError(
                "The 'requests' package is required for the Ollama provider."
            ) from exc
        except Exception as exc:
            raise LLMError(f"Failed to list Ollama models: {exc}") from exc

    def is_available(self) -> bool:
        """Return True if the Ollama server is reachable."""
        try:
            import requests
            response = requests.get(f"{self._host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_host(self) -> str:
        return (
            (self._config.ollama_host if self._config and hasattr(self._config, "ollama_host") else None)
            or os.environ.get("OLLAMA_HOST")
            or self.DEFAULT_HOST
        )

    def _resolve_model(self) -> str:
        return (
            (self._config.ollama_model if self._config and hasattr(self._config, "ollama_model") else None)
            or os.environ.get("OLLAMA_MODEL")
            or self.DEFAULT_MODEL
        )

    @staticmethod
    def _check_http_response(response: Any) -> None:
        """Raise LLMError for non-2xx HTTP responses."""
        if response.status_code == 404:
            raise LLMError(
                f"Ollama model not found (404). "
                f"Pull it first with: ollama pull <model_name>"
            )
        if response.status_code == 500:
            try:
                detail = response.json().get("error", response.text)
            except Exception:
                detail = response.text
            raise LLMError(f"Ollama server error: {detail}")
        if not (200 <= response.status_code < 300):
            raise LLMError(
                f"Ollama returned unexpected status {response.status_code}: {response.text}"
            )

    @staticmethod
    def _map_error(exc: Exception) -> LLMError:
        """Map requests exceptions to LLMError."""
        exc_type = type(exc).__name__
        try:
            import requests
            if isinstance(exc, requests.ConnectionError):
                return LLMError(
                    f"Cannot connect to Ollama. Is it running? "
                    f"Start it with: ollama serve ({exc})"
                )
            if isinstance(exc, requests.Timeout):
                return LLMError(f"Ollama request timed out: {exc}")
            if isinstance(exc, requests.RequestException):
                return LLMError(f"Ollama request error: {exc}")
        except ImportError:
            pass
        return LLMError(f"Ollama provider error ({exc_type}): {exc}")