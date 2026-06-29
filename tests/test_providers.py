"""Tests for LLM provider implementations: error mapping, model defaults, token counting."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.providers.ollama_provider import OllamaProvider
from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
from src.summarizer.llm.providers.openai_provider import OpenAIProvider
from src.summarizer.llm.factory import ProviderFactory, SUPPORTED_PROVIDERS
from src.summarizer.config import Config


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_openai_response(content: str = "Hello from OpenAI") -> MagicMock:
    """Build a mock openai.ChatCompletion-like response."""
    choice = MagicMock()
    choice.message.content = content
    usage = MagicMock()
    usage.__str__ = lambda s: "prompt=10 completion=20"
    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


def _make_anthropic_response(content: str = "Hello from Claude") -> MagicMock:
    """Build a mock anthropic.Message-like response."""
    block = MagicMock()
    block.text = content
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    return response


def _make_ollama_response(content: str = "Hello from Ollama") -> MagicMock:
    """Build a mock requests.Response for Ollama /api/chat."""
    response = MagicMock()
    response.json.return_value = {
        "model": "llama3",
        "message": {"role": "assistant", "content": content},
        "eval_count": 42,
    }
    response.raise_for_status = MagicMock()
    return response


MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarise this article."},
]


# ===========================================================================
# OpenAI Provider
# ===========================================================================

class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def _make_provider(self) -> tuple[OpenAIProvider, MagicMock]:
        """Return (provider, mock_client) with the underlying openai.OpenAI patched."""
        with patch("src.summarizer.llm.providers.openai_provider.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            provider = OpenAIProvider(api_key="sk-test")
        # Patch the already-created client on the instance
        provider._client = mock_client
        return provider, mock_client

    def test_default_model(self) -> None:
        provider, _ = self._make_provider()
        assert provider.get_default_model() == "gpt-4o-mini"

    def test_complete_returns_content(self) -> None:
        provider, mock_client = self._make_provider()
        mock_client.chat.completions.create.return_value = _make_openai_response(
            "Summary here."
        )
        result = provider.complete(MESSAGES)
        assert result == "Summary here."

    def test_complete_passes_messages(self) -> None:
        provider, mock_client = self._make_provider()
        mock_client.chat.completions.create.return_value = _make_openai_response()
        provider.complete(MESSAGES)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"] == MESSAGES

    def test_model_override_in_complete(self) -> None:
        provider, mock_client = self._make_provider()
        mock_client.chat.completions.create.return_value = _make_openai_response()
        provider.complete(MESSAGES, model="gpt-4o")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    def test_auth_error_mapped_to_llm_error(self) -> None:
        import openai

        provider, mock_client = self._make_provider()
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            "bad key", response=MagicMock(), body={}
        )
        with pytest.raises(LLMError, match="authentication"):
            provider.complete(MESSAGES)

    def test_rate_limit_mapped_to_llm_error(self) -> None:
        import openai

        provider, mock_client = self._make_provider()
        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            "rate limited", response=MagicMock(), body={}
        )
        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(MESSAGES)

    def test_api_error_mapped_to_llm_error(self) -> None:
        import openai

        provider, mock_client = self._make_provider()
        mock_client.chat.completions.create.side_effect = openai.APIError(
            "server error", request=MagicMock(), body={}
        )
        with pytest.raises(LLMError, match="API error"):
            provider.complete(MESSAGES)

    def test_empty_response_raises_llm_error(self) -> None:
        provider, mock_client = self._make_provider()
        mock_response = _make_openai_response()
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response
        with pytest.raises(LLMError, match="empty response"):
            provider.complete(MESSAGES)

    def test_count_tokens_returns_int(self) -> None:
        provider, _ = self._make_provider()
        count = provider.count_tokens("Hello, world!")
        assert isinstance(count, int)
        assert count > 0

    def test_missing_api_key_raises_at_factory(self) -> None:
        config = Config()
        config.provider = "openai"
        config.openai_api_key = None
        with pytest.raises(LLMError, match="OpenAI API key"):
            ProviderFactory.create(config)


# ===========================================================================
# Anthropic Provider
# ===========================================================================

class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def _make_provider(self) -> tuple[AnthropicProvider, MagicMock]:
        """Return (provider, mock_anthropic_client) with SDK patched."""
        mock_sdk = MagicMock()
        mock_client = MagicMock()
        mock_sdk.Anthropic.return_value = mock_client
        # Patch the exception classes on the mock SDK
        mock_sdk.AuthenticationError = type("AuthenticationError", (Exception,), {})
        mock_sdk.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_sdk.BadRequestError = type("BadRequestError", (Exception,), {})
        mock_sdk.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_sdk.APIError = type("APIError", (Exception,), {})

        with patch.dict("sys.modules", {"anthropic": mock_sdk}):
            provider = AnthropicProvider(api_key="test-key")

        # Restore the mock sdk and client on the instance
        provider._anthropic = mock_sdk
        provider._client = mock_client
        return provider, mock_client

    def test_default_model(self) -> None:
        provider, _ = self._make_provider()
        assert provider.get_default_model() == "claude-3-5-haiku-20241022"

    def test_complete_returns_content(self) -> None:
        provider, mock_client = self._make_provider()
        mock_client.messages.create.return_value = _make_anthropic_response(
            "Claude summary."
        )
        result = provider.complete(MESSAGES)
        assert result == "Claude summary."

    def test_system_prompt_extracted(self) -> None:
        """System messages should be passed via the 'system' kwarg, not in messages."""
        provider, mock_client = self._make_provider()
        mock_client.messages.create.return_value = _make_anthropic_response()
        provider.complete(MESSAGES)
        call_kwargs = mock_client.messages.create.call_args[1]
        # System prompt should be separate
        assert call_kwargs.get("system") == "You are a helpful assistant."
        # Conversation should only contain user message
        assert all(m["role"] != "system" for m in call_kwargs["messages"])

    def test_no_system_prompt(self) -> None:
        """If there are no system messages, 'system' key should not be in kwargs."""
        provider, mock_client = self._make_provider()
        mock_client.messages.create.return_value = _make_anthropic_response()
        msgs = [{"role": "user", "content": "Hello"}]
        provider.complete(msgs)
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_model_alias_resolved(self) -> None:
        provider, mock_client = self._make_provider()
        mock_client.messages.create.return_value = _make_anthropic_response()
        provider.complete(MESSAGES, model="claude-3-5-sonnet")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"

    def test_auth_error_mapped_to_llm_error(self) -> None:
        provider, mock_client = self._make_provider()
        mock_client.messages.create.side_effect = provider._anthropic.AuthenticationError(
            "bad key"
        )
        with pytest.raises(LLMError, match="authentication"):
            provider.complete(MESSAGES)

    def test_rate_limit_mapped_to_llm_error(self) -> None:
        provider, mock_client = self._make_provider()
        mock_client.messages.create.side_effect = provider._anthropic.RateLimitError(
            "rate limited"
        )
        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(MESSAGES)

    def test_api_error_mapped_to_llm_error(self) -> None:
        provider, mock_client = self._make_provider()
        mock_client.messages.create.side_effect = provider._anthropic.APIError(
            "server error"
        )
        with pytest.raises(LLMError, match="API error"):
            provider.complete(MESSAGES)

    def test_empty_response_raises_llm_error(self) -> None:
        provider, mock_client = self._make_provider()
        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response
        with pytest.raises(LLMError, match="empty response"):
            provider.complete(MESSAGES)

    def test_count_tokens_returns_int(self) -> None:
        provider, _ = self._make_provider()
        count = provider.count_tokens("Hello, world!")
        assert isinstance(count, int)
        assert count > 0

    def test_missing_api_key_raises_at_factory(self) -> None:
        config = Config()
        config.provider = "anthropic"
        config.anthropic_api_key = None
        with pytest.raises(LLMError, match="Anthropic API key"):
            ProviderFactory.create(config)


# ===========================================================================
# Ollama Provider
# ===========================================================================

class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def _make_provider(self) -> tuple[OllamaProvider, MagicMock]:
        """Return (provider, mock_requests) with requests module patched."""
        mock_requests = MagicMock()
        # Patch exception classes used in provider
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.Timeout = TimeoutError
        mock_requests.exceptions.HTTPError = Exception

        with patch.dict("sys.modules", {"requests": mock_requests}):
            provider = OllamaProvider(host="http://localhost:11434", model="llama3")

        provider._requests = mock_requests
        return provider, mock_requests

    def test_default_model(self) -> None:
        provider, _ = self._make_provider()
        assert provider.get_default_model() == "llama3"

    def test_complete_returns_content(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_requests.post.return_value = _make_ollama_response("Ollama summary.")
        result = provider.complete(MESSAGES)
        assert result == "Ollama summary."

    def test_complete_sends_correct_payload(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_requests.post.return_value = _make_ollama_response()
        provider.complete(MESSAGES, temperature=0.5)
        call_args = mock_requests.post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"
        payload = call_args[1]["json"]
        assert payload["model"] == "llama3"
        assert payload["messages"] == MESSAGES
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.5

    def test_model_override_in_complete(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_requests.post.return_value = _make_ollama_response()
        provider.complete(MESSAGES, model="mistral")
        payload = mock_requests.post.call_args[1]["json"]
        assert payload["model"] == "mistral"

    def test_max_tokens_passed_as_num_predict(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_requests.post.return_value = _make_ollama_response()
        provider.complete(MESSAGES, max_tokens=512)
        payload = mock_requests.post.call_args[1]["json"]
        assert payload["options"]["num_predict"] == 512

    def test_connection_error_mapped_to_llm_error(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_requests.post.side_effect = ConnectionError("refused")
        with pytest.raises(LLMError, match="Cannot connect to Ollama"):
            provider.complete(MESSAGES)

    def test_timeout_mapped_to_llm_error(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_requests.post.side_effect = TimeoutError("timed out")
        with pytest.raises(LLMError, match="timed out"):
            provider.complete(MESSAGES)

    def test_empty_content_raises_llm_error(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": ""}
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response
        with pytest.raises(LLMError, match="empty response"):
            provider.complete(MESSAGES)

    def test_malformed_json_response_raises_llm_error(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("not json")
        mock_response.text = "not json"
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response
        with pytest.raises(LLMError, match="non-JSON"):
            provider.complete(MESSAGES)

    def test_list_models_returns_list(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [{"name": "llama3"}, {"name": "mistral"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response
        models = provider.list_models()
        assert models == ["llama3", "mistral"]

    def test_list_models_connection_error(self) -> None:
        provider, mock_requests = self._make_provider()
        mock_requests.get.side_effect = ConnectionError("refused")
        with pytest.raises(LLMError, match="Cannot connect to Ollama"):
            provider.list_models()

    def test_count_tokens_returns_int(self) -> None:
        provider, _ = self._make_provider()
        count = provider.count_tokens("Hello, world!")
        assert isinstance(count, int)
        assert count > 0

    def test_custom_host(self) -> None:
        """Provider should use the supplied host URL."""
        mock_requests = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.Timeout = TimeoutError
        mock_requests.exceptions.HTTPError = Exception

        with patch.dict("sys.modules", {"requests": mock_requests}):
            provider = OllamaProvider(host="http://my-server:11434")

        provider._requests = mock_requests
        assert provider._host == "http://my-server:11434"

    def test_ollama_created_by_factory_without_key(self) -> None:
        """Ollama requires no API key and should be created successfully."""
        mock_requests = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.Timeout = TimeoutError
        mock_requests.exceptions.HTTPError = Exception

        config = Config()
        config.provider = "ollama"
        config.model = "llama3"

        with patch.dict("sys.modules", {"requests": mock_requests}):
            provider = ProviderFactory.create(config)

        assert isinstance(provider, OllamaProvider)


# ===========================================================================
# ProviderFactory
# ===========================================================================

class TestProviderFactory:
    """Tests for the ProviderFactory."""

    def test_supported_providers_constant(self) -> None:
        assert set(SUPPORTED_PROVIDERS) == {"openai", "anthropic", "ollama"}

    def test_unknown_provider_raises_llm_error(self) -> None:
        config = Config()
        config.provider = "grok"
        with pytest.raises(LLMError, match="Unknown LLM provider"):
            ProviderFactory.create(config)

    def test_factory_creates_openai_provider(self) -> None:
        config = Config()
        config.provider = "openai"
        config.openai_api_key = "sk-test"

        with patch(
            "src.summarizer.llm.providers.openai_provider.OpenAI"
        ) as MockOpenAI:
            MockOpenAI.return_value = MagicMock()
            provider = ProviderFactory.create(config)

        assert isinstance(provider, OpenAIProvider)

    def test_factory_creates_anthropic_provider(self) -> None:
        config = Config()
        config.provider = "anthropic"
        config.anthropic_api_key = "test-key"

        mock_sdk = MagicMock()
        mock_sdk.AuthenticationError = Exception
        mock_sdk.RateLimitError = Exception
        mock_sdk.BadRequestError = Exception
        mock_sdk.APIConnectionError = Exception
        mock_sdk.APIError = Exception

        with patch.dict("sys.modules", {"anthropic": mock_sdk}):
            provider = ProviderFactory.create(config)

        assert isinstance(provider, AnthropicProvider)

    def test_factory_creates_ollama_provider(self) -> None:
        config = Config()
        config.provider = "ollama"

        mock_requests = MagicMock()
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.Timeout = TimeoutError
        mock_requests.exceptions.HTTPError = Exception

        with patch.dict("sys.modules", {"requests": mock_requests}):
            provider = ProviderFactory.create(config)

        assert isinstance(provider, OllamaProvider)

    def test_provider_name_is_case_insensitive(self) -> None:
        config = Config()
        config.provider = "OpenAI"
        config.openai_api_key = "sk-test"

        with patch(
            "src.summarizer.llm.providers.openai_provider.OpenAI"
        ) as MockOpenAI:
            MockOpenAI.return_value = MagicMock()
            provider = ProviderFactory.create(config)

        assert isinstance(provider, OpenAIProvider)