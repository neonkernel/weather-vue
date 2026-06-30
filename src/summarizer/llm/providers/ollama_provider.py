"""Ollama local LLM provider implementation."""

from typing import Any

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider
from src.summarizer.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_OLLAMA_HOST = "http://localhost:11434"
_CHARS_PER_TOKEN = 4


class OllamaProvider(BaseLLMProvider):
    """LLM provider backed by a local Ollama REST API instance."""

    DEFAULT_MODEL = "llama3"

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        timeout: int = 120,
    ) -> None:
        try:
            import requests
            self._requests = requests
        except ImportError as exc:
            raise LLMError(
                "The 'requests' package is not installed. "
                "Run: pip install requests"
            ) from exc

        self._host = (host or _DEFAULT_OLLAMA_HOST).rstrip("/")
        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def list_models(self) -> list[str]:
        """Return a list of models available on the local Ollama instance."""
        url = f"{self._host}/api/tags"
        try:
            response = self._requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except self._requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Is Ollama running? Try: ollama serve"
            ) from exc
        except self._requests.exceptions.HTTPError as exc:
            raise LLMError(f"Ollama API error listing models: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected error listing Ollama models: {exc}") from exc

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Call the Ollama /api/chat endpoint."""
        model = kwargs.get("model", self._model)
        temperature = kwargs.get("temperature", self._temperature)
        max_tokens = kwargs.get("max_tokens", self._max_tokens)

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
            "OllamaProvider.complete: model=%s, messages=%d, host=%s",
            model,
            len(messages),
            self._host,
        )

        try:
            response = self._requests.post(
                url,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Ollama /api/chat response shape: {"message": {"role": "assistant", "content": "..."}}
            content = data.get("message", {}).get("content")
            if not content:
                raise LLMError("Ollama returned an empty response.")
            return content.strip()

        except self._requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self._host}. "
                "Is Ollama running? Try: ollama serve"
            ) from exc
        except self._requests.exceptions.Timeout as exc:
            raise LLMError(
                f"Ollama request timed out after {self._timeout}s. "
                "The model may still be loading."
            ) from exc
        except self._requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            body = ""
            if exc.response is not None:
                try:
                    body = exc.response.json().get("error", exc.response.text)
                except Exception:
                    body = exc.response.text
            raise LLMError(
                f"Ollama API HTTP {status} error: {body}"
            ) from exc
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Unexpected error calling Ollama: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """Character-based heuristic token count (~4 chars per token)."""
        return max(1, len(text) // _CHARS_PER_TOKEN)