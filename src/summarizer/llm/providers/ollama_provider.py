"""Ollama local LLM provider."""

from __future__ import annotations

import json
import os
from typing import Any, TYPE_CHECKING

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from src.summarizer.config import Config


class OllamaProvider(BaseLLMProvider):
    """LLM provider that calls a local Ollama instance via its REST API."""

    DEFAULT_MODEL = "llama3.2"
    DEFAULT_HOST = "http://localhost:11434"

    def __init__(self, config: "Config | None" = None) -> None:
        self._config = config
        self._host = (
            (config.ollama_host if config and hasattr(config, "ollama_host") and config.ollama_host else None)
            or os.environ.get("OLLAMA_HOST", self.DEFAULT_HOST)
        ).rstrip("/")

        try:
            import requests  # noqa: F401 — ensure requests is available
        except ImportError as exc:
            raise LLMError(
                "The 'requests' package is required for the Ollama provider. "
                "Install it with: pip install requests"
            ) from exc

        self._model = (
            (config.model if config and hasattr(config, "model") and config.model else None)
            or os.environ.get("DEFAULT_MODEL")
            or self.DEFAULT_MODEL
        )

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def count_tokens(self, text: str) -> int:
        """Character-based heuristic: ~4 chars per token."""
        return max(1, len(text) // 4)

    def list_models(self) -> list[str]:
        """Query Ollama for available models."""
        import requests

        try:
            response = requests.get(f"{self._host}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            raise LLMError(f"Failed to list Ollama models: {exc}") from exc

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send a chat completion request to the local Ollama API.

        Uses the /api/chat endpoint (Ollama >= 0.1.14).
        """
        import requests

        model = kwargs.pop("model", self._model)
        # Ollama does not use max_tokens / temperature in the same way;
        # pass them through the options dict if provided.
        temperature = kwargs.pop("temperature", None)
        max_tokens = kwargs.pop("max_tokens", None)

        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        payload.update(kwargs)

        url = f"{self._host}/api/chat"
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content")
            if not content:
                raise LLMError("Ollama returned an empty response.")
            return content
        except LLMError:
            raise
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Make sure Ollama is running (`ollama serve`)."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            try:
                detail = exc.response.json() if exc.response is not None else {}
            except Exception:
                detail = {}
            raise LLMError(
                f"Ollama API returned HTTP {status}: {detail.get('error', str(exc))}"
            ) from exc
        except Exception as exc:
            raise LLMError(f"Ollama API error: {exc}") from exc