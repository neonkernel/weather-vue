"""Ollama local LLM provider implementation."""

import os
from typing import Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from ..base import BaseLLMProvider
from ...exceptions import LLMError


class OllamaProvider(BaseLLMProvider):
    """
    Ollama provider that communicates with a local Ollama instance via HTTP.

    Expects Ollama to be running at http://localhost:11434 (or OLLAMA_HOST).
    """

    DEFAULT_MODEL = "llama3"
    DEFAULT_HOST = "http://localhost:11434"
    # Approximate characters per token for open-source models
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: int = 120,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Ollama provider.

        Args:
            host: Base URL for the Ollama REST API. Falls back to OLLAMA_HOST env var
                  and then to DEFAULT_HOST.
            model: Model name to use. Falls back to DEFAULT_MODEL.
            timeout: HTTP request timeout in seconds (default 120 for local inference).
            **kwargs: Additional options (currently unused).
        """
        if not HAS_REQUESTS:
            raise LLMError(
                "requests package is not installed. Run: pip install requests"
            )

        self._host = (
            host
            or os.environ.get("OLLAMA_HOST")
            or self.DEFAULT_HOST
        ).rstrip("/")
        self._model = model or self.DEFAULT_MODEL
        self._timeout = timeout

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "ollama"

    def list_models(self) -> list[str]:
        """
        Retrieve the list of models available in the local Ollama instance.

        Returns:
            List of model name strings.

        Raises:
            LLMError: If the request fails.
        """
        try:
            import requests  # noqa: PLC0415
            response = requests.get(
                f"{self._host}/api/tags",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            raise LLMError(f"Failed to list Ollama models: {exc}") from exc

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send messages to Ollama using the /api/chat endpoint and return the response.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Additional options. Recognises 'model', 'temperature'.

        Returns:
            The assistant's response text.

        Raises:
            LLMError: If the request fails.
        """
        import requests  # noqa: PLC0415

        model = kwargs.pop("model", self._model)
        temperature = kwargs.pop("temperature", 0.3)
        # Ollama /api/chat supports options dict
        options: dict[str, Any] = {"temperature": temperature}
        options.update(kwargs.pop("options", {}))

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        try:
            response = requests.post(
                f"{self._host}/api/chat",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Ollama /api/chat returns {"message": {"role": "assistant", "content": "..."}}
            content = data.get("message", {}).get("content")
            if not content:
                raise LLMError("Ollama returned an empty response.")
            return content

        except LLMError:
            raise
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Make sure Ollama is running (ollama serve)."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise LLMError(
                f"Ollama request timed out after {self._timeout}s."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            try:
                detail = exc.response.json() if exc.response is not None else {}
            except Exception:
                detail = {}
            raise LLMError(
                f"Ollama HTTP error {status}: {detail.get('error', str(exc))}"
            ) from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error from Ollama provider: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """Estimate token count using a character-based heuristic."""
        return max(1, len(text) // self.CHARS_PER_TOKEN)