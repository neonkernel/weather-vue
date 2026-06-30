"""Ollama local LLM provider implementation using the Ollama REST API."""

from typing import Any

from ...exceptions import LLMError
from ...logger import get_logger
from ..base import BaseLLMProvider

logger = get_logger(__name__)

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


class OllamaProvider(BaseLLMProvider):
    """
    Provider for locally-running Ollama models.
    Communicates via the Ollama REST API (default: http://localhost:11434).
    """

    DEFAULT_MODEL = "llama3.2"
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_MAX_TOKENS = 4096
    REQUEST_TIMEOUT = 120  # seconds — local models can be slow

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
    ) -> None:
        if not _REQUESTS_AVAILABLE:
            raise LLMError(
                "requests package is not installed. Run: pip install requests"
            )

        self._host = (host or self.DEFAULT_HOST).rstrip("/")
        self._model = model or self.DEFAULT_MODEL
        logger.debug(
            "OllamaProvider initialized: host=%s, model=%s",
            self._host,
            self._model,
        )

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "ollama"

    def list_models(self) -> list[str]:
        """Return a list of model names available on the local Ollama instance."""
        url = f"{self._host}/api/tags"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Is Ollama running? Start it with: ollama serve"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise LLMError(f"Ollama API error listing models: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error listing Ollama models: {exc}") from exc

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Call the Ollama /api/chat endpoint (non-streaming).

        Ollama's chat endpoint accepts the same message format as OpenAI
        (role + content), so no translation is needed.
        """
        model = kwargs.get("model", self._model)
        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        url = f"{self._host}/api/chat"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        logger.debug(
            "Ollama request: host=%s, model=%s, messages=%d",
            self._host,
            model,
            len(messages),
        )

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            content: str = data.get("message", {}).get("content", "")
            logger.debug(
                "Ollama response received, length=%d chars", len(content)
            )
            return content

        except requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Is Ollama running? Start it with: ollama serve"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise LLMError(
                f"Ollama request timed out after {self.REQUEST_TIMEOUT}s. "
                "The model may be loading — try again."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            if status == 404:
                raise LLMError(
                    f"Model '{model}' not found on Ollama. "
                    f"Pull it first with: ollama pull {model}"
                ) from exc
            raise LLMError(f"Ollama HTTP error {status}: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error calling Ollama: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """
        Ollama doesn't expose a token-counting endpoint.
        Use a character-based heuristic: ~4 chars per token.
        """
        return max(1, len(text) // 4)