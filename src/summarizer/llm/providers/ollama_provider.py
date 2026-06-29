"""Ollama local LLM provider implementation."""

import json
import os
from typing import TYPE_CHECKING

import requests

from ...exceptions import LLMError
from ..base import BaseLLMProvider

if TYPE_CHECKING:
    from ...config import Config

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"
REQUEST_TIMEOUT = 120  # seconds – local models can be slow


class OllamaProvider(BaseLLMProvider):
    """LLM provider backed by a local Ollama instance via its REST API."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.host = (
            getattr(config, "ollama_host", None)
            or os.environ.get("OLLAMA_HOST", DEFAULT_HOST)
        ).rstrip("/")

    def get_default_model(self) -> str:
        return getattr(self.config, "model", None) or DEFAULT_MODEL

    def list_models(self) -> list:
        """
        Query the Ollama instance for available models.

        Returns:
            List of model name strings.

        Raises:
            LLMError: If the Ollama API is unreachable.
        """
        url = f"{self.host}/api/tags"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except requests.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self.host}. "
                "Ensure Ollama is running: ollama serve"
            ) from exc
        except requests.HTTPError as exc:
            raise LLMError(f"Ollama API error listing models: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error listing Ollama models: {exc}") from exc

    def complete(self, messages: list, **kwargs) -> str:
        """
        Call the Ollama chat completions endpoint.

        Uses the /api/chat endpoint which accepts OpenAI-compatible message format.

        Args:
            messages: List of {'role': ..., 'content': ...} dicts.
            **kwargs: Overrides for model, temperature, etc.

        Returns:
            The assistant's reply text.

        Raises:
            LLMError: On connection or API errors.
        """
        model = kwargs.get("model") or self.get_default_model()
        temperature = kwargs.get("temperature")
        if temperature is None:
            temperature = getattr(self.config, "temperature", 0.3)

        url = f"{self.host}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        # Ollama respects num_predict (≈ max_tokens)
        max_tokens = kwargs.get("max_tokens") or getattr(self.config, "max_tokens", None)
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            # Ollama chat response: {"message": {"role": "assistant", "content": "..."}}
            return data.get("message", {}).get("content", "")
        except requests.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self.host}. "
                "Ensure Ollama is running: ollama serve"
            ) from exc
        except requests.Timeout as exc:
            raise LLMError(
                f"Ollama request timed out after {REQUEST_TIMEOUT}s. "
                "The model may still be loading; try again."
            ) from exc
        except requests.HTTPError as exc:
            # Try to extract a useful message from the response body
            try:
                detail = exc.response.json().get("error", str(exc))
            except Exception:
                detail = str(exc)
            raise LLMError(f"Ollama HTTP error: {detail}") from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"Invalid JSON response from Ollama: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling Ollama: {exc}") from exc