"""Tests for LLM provider implementations."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.summarizer.exceptions import LLMError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarize: The sky is blue."},
]


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def _make_provider(self, api_key: str = "sk-test") -> Any:
        """Create an OpenAIProvider with a mocked openai client."""
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        with patch("src.summarizer.llm.providers.openai_provider.OpenAI") as mock_cls:
            provider = OpenAIProvider(api_key=api_key)
        provider._client = MagicMock()
        return provider

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "openai"

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "gpt-4o"

    def test_complete_returns_text(self):
        provider = self._make_provider()

        mock_choice = MagicMock()
        mock_choice.message.content = "The sky is blue."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        provider._client.chat.completions.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "The sky is blue."

    def test_complete_raises_llm_error_on_auth_failure(self):
        from openai import AuthenticationError as OAIAuthError

        provider = self._make_provider()
        # Build a realistic AuthenticationError
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_response.headers = {}
        provider._client.chat.completions.create.side_effect = OAIAuthError(
            message="Invalid API key",
            response=mock_response,
            body={"error": {"message": "Invalid API key"}},
        )

        with pytest.raises(LLMError, match="authentication"):
            provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_llm_error_on_rate_limit(self):
        from openai import RateLimitError as OAIRateLimitError

        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {}
        mock_response.headers = {}
        provider._client.chat.completions.create.side_effect = OAIRateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body={},
        )

        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_empty_response(self):
        provider = self._make_provider()
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        provider._client.chat.completions.create.return_value = mock_response

        with pytest.raises(LLMError, match="empty"):
            provider.complete(SAMPLE_MESSAGES)

    def test_count_tokens_heuristic_fallback(self):
        """When tiktoken is unavailable, falls back to char-based count."""
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        with patch("src.summarizer.llm.providers.openai_provider.OpenAI"):
            provider = OpenAIProvider(api_key="sk-test")
        provider._encoder = None  # Force heuristic

        count = provider.count_tokens("Hello world!")
        assert count >= 1

    def test_count_tokens_uses_tiktoken(self):
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = [1, 2, 3]  # 3 tokens

        with patch("src.summarizer.llm.providers.openai_provider.OpenAI"):
            provider = OpenAIProvider(api_key="sk-test")
        provider._encoder = mock_encoder

        assert provider.count_tokens("test text") == 3

    def test_missing_api_key_raises(self):
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        with patch.dict("os.environ", {}, clear=True):
            # Ensure OPENAI_API_KEY is not set
            import os
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(LLMError, match="API key"):
                OpenAIProvider(api_key=None)


# ---------------------------------------------------------------------------
# Anthropic Provider
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def _make_provider(self, api_key: str = "sk-ant-test") -> Any:
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider

        with patch("src.summarizer.llm.providers.anthropic_provider.Anthropic") as mock_cls:
            provider = AnthropicProvider(api_key=api_key)
        provider._client = MagicMock()
        return provider

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "anthropic"

    def test_default_model(self):
        provider = self._make_provider()
        assert "claude" in provider.default_model.lower()

    def test_complete_returns_text(self):
        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "The sky is blue."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "The sky is blue."

    def test_system_messages_extracted(self):
        """System messages should be passed as 'system' kwarg, not in messages list."""
        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "OK"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES)

        call_kwargs = provider._client.messages.create.call_args
        # 'messages' kwarg should not contain system role
        sent_messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages", [])
        roles = [m["role"] for m in sent_messages]
        assert "system" not in roles

    def test_complete_raises_llm_error_on_auth_failure(self):
        from anthropic import AuthenticationError as AntAuthError

        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}
        mock_response.headers = {}
        provider._client.messages.create.side_effect = AntAuthError(
            message="Unauthorized",
            response=mock_response,
            body={},
        )

        with pytest.raises(LLMError, match="authentication"):
            provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_empty_response(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.content = []
        provider._client.messages.create.return_value = mock_response

        with pytest.raises(LLMError, match="empty"):
            provider.complete(SAMPLE_MESSAGES)

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        text = "a" * 400  # 400 chars → ~100 tokens
        count = provider.count_tokens(text)
        assert count == 100

    def test_missing_api_key_raises(self):
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider

        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(LLMError, match="API key"):
            AnthropicProvider(api_key=None)


# ---------------------------------------------------------------------------
# Ollama Provider
# ---------------------------------------------------------------------------

class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def _make_provider(self, host: str = "http://localhost:11434") -> Any:
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider
        return OllamaProvider(host=host, model="llama3")

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "ollama"

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "llama3"

    def test_complete_returns_text(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "The sky is blue."}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = provider.complete(SAMPLE_MESSAGES)

        assert result == "The sky is blue."

    def test_complete_sends_correct_payload(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "OK"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            provider.complete(SAMPLE_MESSAGES, temperature=0.5)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["model"] == "llama3"
        assert payload["stream"] is False
        assert payload["messages"] == SAMPLE_MESSAGES
        assert payload["options"]["temperature"] == 0.5

    def test_complete_raises_on_connection_error(self):
        import requests as req_lib
        provider = self._make_provider()

        with patch("requests.post", side_effect=req_lib.exceptions.ConnectionError("refused")):
            with pytest.raises(LLMError, match="connect"):
                provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_timeout(self):
        import requests as req_lib
        provider = self._make_provider()

        with patch("requests.post", side_effect=req_lib.exceptions.Timeout()):
            with pytest.raises(LLMError, match="timed out"):
                provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_http_error(self):
        import requests as req_lib
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "model not found"}
        http_error = req_lib.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(LLMError, match="model not found"):
                provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_empty_response(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"role": "assistant", "content": ""}}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(LLMError, match="empty"):
                provider.complete(SAMPLE_MESSAGES)

    def test_list_models(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [{"name": "llama3"}, {"name": "mistral"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            models = provider.list_models()

        assert models == ["llama3", "mistral"]

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        text = "a" * 800  # 800 chars → 200 tokens
        assert provider.count_tokens(text) == 200

    def test_custom_host_from_env(self):
        import os
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        with patch.dict(os.environ, {"OLLAMA_HOST": "http://myhost:11434"}):
            provider = OllamaProvider()
        assert provider._host == "http://myhost:11434"

    def test_trailing_slash_stripped_from_host(self):
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider(host="http://localhost:11434/")
        assert provider._host == "http://localhost:11434"


# ---------------------------------------------------------------------------
# ProviderFactory
# ---------------------------------------------------------------------------

class TestProviderFactory:
    """Tests for ProviderFactory and create_provider."""

    def test_factory_returns_openai_provider(self):
        from src.summarizer.config import Config
        from src.summarizer.llm.factory import create_provider
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        config = Config(provider="openai", openai_api_key="sk-test")
        with patch("src.summarizer.llm.providers.openai_provider.OpenAI"):
            provider = create_provider(config)
        assert isinstance(provider, OpenAIProvider)

    def test_factory_returns_anthropic_provider(self):
        from src.summarizer.config import Config
        from src.summarizer.llm.factory import create_provider
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider

        config = Config(provider="anthropic", anthropic_api_key="sk-ant-test")
        with patch("src.summarizer.llm.providers.anthropic_provider.Anthropic"):
            provider = create_provider(config)
        assert isinstance(provider, AnthropicProvider)

    def test_factory_returns_ollama_provider(self):
        from src.summarizer.config import Config
        from src.summarizer.llm.factory import create_provider
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        config = Config(provider="ollama")
        provider = create_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_factory_raises_on_unknown_provider(self):
        from src.summarizer.config import Config
        from src.summarizer.llm.factory import create_provider

        config = Config(provider="grok")
        with pytest.raises(LLMError, match="Unknown LLM provider"):
            create_provider(config)

    def test_factory_available_providers(self):
        from src.summarizer.llm.factory import ProviderFactory

        factory = ProviderFactory()
        providers = factory.available_providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_factory_register_custom_provider(self):
        from src.summarizer.config import Config
        from src.summarizer.llm.base import BaseLLMProvider
        from src.summarizer.llm.factory import ProviderFactory

        class DummyProvider(BaseLLMProvider):
            @property
            def default_model(self): return "dummy-1"
            @property
            def provider_name(self): return "dummy"
            def complete(self, messages, **kwargs): return "dummy response"
            def count_tokens(self, text): return len(text)

        factory = ProviderFactory()
        factory.register("dummy", DummyProvider)
        assert "dummy" in factory.available_providers


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------

class TestConfigProviderFields:
    """Tests that Config correctly handles provider-related fields."""

    def test_default_provider_is_openai(self):
        from src.summarizer.config import Config
        config = Config()
        assert config.provider == "openai"

    def test_from_env_reads_llm_provider(self):
        import os
        from src.summarizer.config import Config

        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}):
            config = Config.from_env()
        assert config.provider == "anthropic"

    def test_from_env_reads_anthropic_api_key(self):
        import os
        from src.summarizer.config import Config

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-xyz"}):
            config = Config.from_env()
        assert config.anthropic_api_key == "sk-ant-xyz"

    def test_from_env_reads_ollama_host(self):
        import os
        from src.summarizer.config import Config

        with patch.dict(os.environ, {"OLLAMA_HOST": "http://gpu-box:11434"}):
            config = Config.from_env()
        assert config.ollama_host == "http://gpu-box:11434"

    def test_merge_cli_args_overrides_provider(self):
        from src.summarizer.config import Config

        config = Config(provider="openai")
        updated = config.merge_cli_args(provider="ollama")
        assert updated.provider == "ollama"
        assert config.provider == "openai"  # original unchanged

    def test_merge_cli_args_ignores_none(self):
        from src.summarizer.config import Config

        config = Config(provider="anthropic")
        updated = config.merge_cli_args(provider=None)
        assert updated.provider == "anthropic"