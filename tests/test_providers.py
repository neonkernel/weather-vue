"""Tests for each LLM provider: mocked HTTP/SDK responses, error mapping, model defaults."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.summarizer.exceptions import LLMError


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarize this text."},
]


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI Provider Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def _make_provider(self, api_key: str = "sk-test", model: str | None = None):
        """Create an OpenAIProvider with mocked OpenAI client."""
        with patch("src.summarizer.llm.providers.openai_provider._OPENAI_AVAILABLE", True):
            with patch("src.summarizer.llm.providers.openai_provider.OpenAI") as mock_openai_cls:
                from src.summarizer.llm.providers.openai_provider import OpenAIProvider
                provider = OpenAIProvider(api_key=api_key, model=model)
                provider._client = mock_openai_cls.return_value
                return provider, mock_openai_cls.return_value

    def test_provider_name(self):
        provider, _ = self._make_provider()
        assert provider.provider_name == "openai"

    def test_default_model(self):
        provider, _ = self._make_provider()
        assert provider.default_model == "gpt-4o"

    def test_custom_model(self):
        provider, _ = self._make_provider(model="gpt-4-turbo")
        assert provider._model == "gpt-4-turbo"

    def test_complete_success(self):
        provider, mock_client = self._make_provider()

        mock_choice = MagicMock()
        mock_choice.message.content = "This is a test summary."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "This is a test summary."
        mock_client.chat.completions.create.assert_called_once()

    def test_complete_passes_kwargs(self):
        provider, mock_client = self._make_provider()

        mock_choice = MagicMock()
        mock_choice.message.content = "Summary."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES, temperature=0.7, max_tokens=100)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 100

    def test_complete_raises_on_missing_api_key(self):
        with patch("src.summarizer.llm.providers.openai_provider._OPENAI_AVAILABLE", True):
            with patch("src.summarizer.llm.providers.openai_provider.OpenAI"):
                from src.summarizer.llm.providers.openai_provider import OpenAIProvider
                with pytest.raises(LLMError, match="API key"):
                    OpenAIProvider(api_key="")

    def test_complete_maps_authentication_error(self):
        provider, mock_client = self._make_provider()

        from openai import AuthenticationError as OAIAuthError
        # AuthenticationError requires a specific constructor in newer openai SDK
        mock_client.chat.completions.create.side_effect = OAIAuthError(
            message="Invalid API key",
            response=MagicMock(status_code=401, headers={}),
            body={"error": {"message": "Invalid API key"}},
        )

        with pytest.raises(LLMError, match="authentication"):
            provider.complete(SAMPLE_MESSAGES)

    def test_complete_maps_rate_limit_error(self):
        provider, mock_client = self._make_provider()

        from openai import RateLimitError as OAIRateLimitError
        mock_client.chat.completions.create.side_effect = OAIRateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit exceeded"}},
        )

        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(SAMPLE_MESSAGES)

    def test_count_tokens_fallback(self):
        """When tiktoken is not available, use character-based heuristic."""
        provider, _ = self._make_provider()

        with patch("src.summarizer.llm.providers.openai_provider._TIKTOKEN_AVAILABLE", False):
            count = provider.count_tokens("Hello world")
            assert count >= 1

    def test_count_tokens_with_tiktoken(self):
        provider, _ = self._make_provider()

        with patch("src.summarizer.llm.providers.openai_provider._TIKTOKEN_AVAILABLE", True):
            with patch("src.summarizer.llm.providers.openai_provider.tiktoken") as mock_tiktoken:
                mock_enc = MagicMock()
                mock_enc.encode.return_value = [1, 2, 3]
                mock_tiktoken.encoding_for_model.return_value = mock_enc

                count = provider.count_tokens("Hello world")
                assert count == 3

    def test_not_available_raises(self):
        with patch("src.summarizer.llm.providers.openai_provider._OPENAI_AVAILABLE", False):
            # Re-import to pick up the patched value
            import importlib
            import src.summarizer.llm.providers.openai_provider as mod
            importlib.reload(mod)
            # Reload resets the class; patch the flag directly on the module
            mod._OPENAI_AVAILABLE = False
            with pytest.raises(LLMError, match="openai package"):
                mod.OpenAIProvider(api_key="sk-test")


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic Provider Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def _make_provider(self, api_key: str = "ant-test", model: str | None = None):
        with patch("src.summarizer.llm.providers.anthropic_provider._ANTHROPIC_AVAILABLE", True):
            with patch("src.summarizer.llm.providers.anthropic_provider.Anthropic") as mock_cls:
                from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
                provider = AnthropicProvider(api_key=api_key, model=model)
                provider._client = mock_cls.return_value
                return provider, mock_cls.return_value

    def test_provider_name(self):
        provider, _ = self._make_provider()
        assert provider.provider_name == "anthropic"

    def test_default_model(self):
        provider, _ = self._make_provider()
        assert provider.default_model == "claude-3-5-sonnet-20241022"

    def test_custom_model(self):
        provider, _ = self._make_provider(model="claude-3-opus-20240229")
        assert provider._model == "claude-3-opus-20240229"

    def test_complete_success(self):
        provider, mock_client = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "Anthropic summary."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Anthropic summary."

    def test_system_prompt_extracted(self):
        provider, mock_client = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "Response."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are a helpful assistant."
        # System message should NOT appear in 'messages'
        for msg in call_kwargs["messages"]:
            assert msg["role"] != "system"

    def test_no_system_prompt_in_messages_only(self):
        provider, mock_client = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "Response."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        messages_no_system = [{"role": "user", "content": "Hello"}]
        provider.complete(messages_no_system)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_raises_on_missing_api_key(self):
        with patch("src.summarizer.llm.providers.anthropic_provider._ANTHROPIC_AVAILABLE", True):
            with patch("src.summarizer.llm.providers.anthropic_provider.Anthropic"):
                from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
                with pytest.raises(LLMError, match="API key"):
                    AnthropicProvider(api_key="")

    def test_maps_authentication_error(self):
        provider, mock_client = self._make_provider()

        from anthropic import AuthenticationError as AntAuthError
        mock_client.messages.create.side_effect = AntAuthError(
            message="Invalid API key",
            response=MagicMock(status_code=401, headers={}),
            body={"type": "error"},
        )

        with pytest.raises(LLMError, match="authentication"):
            provider.complete(SAMPLE_MESSAGES)

    def test_maps_rate_limit_error(self):
        provider, mock_client = self._make_provider()

        from anthropic import RateLimitError as AntRateLimitError
        mock_client.messages.create.side_effect = AntRateLimitError(
            message="Rate limit",
            response=MagicMock(status_code=429, headers={}),
            body={"type": "error"},
        )

        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(SAMPLE_MESSAGES)

    def test_count_tokens_heuristic(self):
        provider, _ = self._make_provider()
        # "Hello world" is 11 chars → ~3 tokens at 3.5 chars/token
        count = provider.count_tokens("Hello world")
        assert count >= 1

    def test_count_tokens_empty_string(self):
        provider, _ = self._make_provider()
        count = provider.count_tokens("")
        assert count >= 1  # min is 1

    def test_multiple_content_blocks(self):
        """Response with multiple text blocks should be concatenated."""
        provider, mock_client = self._make_provider()

        block1 = MagicMock()
        block1.text = "Part one. "
        block2 = MagicMock()
        block2.text = "Part two."
        mock_response = MagicMock()
        mock_response.content = [block1, block2]
        mock_client.messages.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Part one. Part two."


# ─────────────────────────────────────────────────────────────────────────────
# Ollama Provider Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOllamaProvider:
    """Tests for OllamaProvider using mocked requests."""

    def _make_provider(self, host: str | None = None, model: str | None = None):
        with patch("src.summarizer.llm.providers.ollama_provider._REQUESTS_AVAILABLE", True):
            from src.summarizer.llm.providers.ollama_provider import OllamaProvider
            return OllamaProvider(host=host, model=model)

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "ollama"

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "llama3.2"

    def test_default_host(self):
        provider = self._make_provider()
        assert provider._host == "http://localhost:11434"

    def test_custom_host_trailing_slash_stripped(self):
        provider = self._make_provider(host="http://myserver:11434/")
        assert provider._host == "http://myserver:11434"

    def test_custom_model(self):
        provider = self._make_provider(model="mistral")
        assert provider._model == "mistral"

    def test_complete_success(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "Ollama summary."}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("src.summarizer.llm.providers.ollama_provider.requests.post",
                   return_value=mock_response) as mock_post:
            result = provider.complete(SAMPLE_MESSAGES)

        assert result == "Ollama summary."
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["stream"] is False
        assert call_kwargs["json"]["messages"] == SAMPLE_MESSAGES

    def test_complete_uses_custom_model_kwarg(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "ok"}}
        mock_response.raise_for_status = MagicMock()

        with patch("src.summarizer.llm.providers.ollama_provider.requests.post",
                   return_value=mock_response) as mock_post:
            provider.complete(SAMPLE_MESSAGES, model="phi3")

        call_json = mock_post.call_args[1]["json"]
        assert call_json["model"] == "phi3"

    def test_complete_connection_error(self):
        import requests as req
        provider = self._make_provider()

        with patch("src.summarizer.llm.providers.ollama_provider.requests.post",
                   side_effect=req.exceptions.ConnectionError("refused")):
            with pytest.raises(LLMError, match="Cannot connect to Ollama"):
                provider.complete(SAMPLE_MESSAGES)

    def test_complete_timeout_error(self):
        import requests as req
        provider = self._make_provider()

        with patch("src.summarizer.llm.providers.ollama_provider.requests.post",
                   side_effect=req.exceptions.Timeout("timed out")):
            with pytest.raises(LLMError, match="timed out"):
                provider.complete(SAMPLE_MESSAGES)

    def test_complete_404_model_not_found(self):
        import requests as req
        provider = self._make_provider(model="nonexistent-model")

        mock_http_error_response = MagicMock()
        mock_http_error_response.status_code = 404
        http_error = req.exceptions.HTTPError(response=mock_http_error_response)

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = http_error

        with patch("src.summarizer.llm.providers.ollama_provider.requests.post",
                   return_value=mock_response):
            with pytest.raises(LLMError, match="not found on Ollama"):
                provider.complete(SAMPLE_MESSAGES)

    def test_list_models_success(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
                {"name": "phi3"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("src.summarizer.llm.providers.ollama_provider.requests.get",
                   return_value=mock_response):
            models = provider.list_models()

        assert models == ["llama3.2", "mistral", "phi3"]

    def test_list_models_connection_error(self):
        import requests as req
        provider = self._make_provider()

        with patch("src.summarizer.llm.providers.ollama_provider.requests.get",
                   side_effect=req.exceptions.ConnectionError("refused")):
            with pytest.raises(LLMError, match="Cannot connect to Ollama"):
                provider.list_models()

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        count = provider.count_tokens("Hello world")
        assert count >= 1

    def test_count_tokens_empty(self):
        provider = self._make_provider()
        count = provider.count_tokens("")
        assert count >= 1


# ─────────────────────────────────────────────────────────────────────────────
# ProviderFactory Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderFactory:
    """Tests for ProviderFactory."""

    def _make_config(self, **kwargs: Any):
        from src.summarizer.config import SummarizerConfig
        config = SummarizerConfig()
        for k, v in kwargs.items():
            setattr(config, k, v)
        return config

    def test_creates_openai_provider(self):
        config = self._make_config(provider="openai", openai_api_key="sk-test")

        with patch("src.summarizer.llm.providers.openai_provider._OPENAI_AVAILABLE", True):
            with patch("src.summarizer.llm.providers.openai_provider.OpenAI"):
                from src.summarizer.llm.factory import ProviderFactory
                from src.summarizer.llm.providers.openai_provider import OpenAIProvider
                provider = ProviderFactory.create(config)
                assert isinstance(provider, OpenAIProvider)

    def test_creates_anthropic_provider(self):
        config = self._make_config(provider="anthropic", anthropic_api_key="ant-test")

        with patch("src.summarizer.llm.providers.anthropic_provider._ANTHROPIC_AVAILABLE", True):
            with patch("src.summarizer.llm.providers.anthropic_provider.Anthropic"):
                from src.summarizer.llm.factory import ProviderFactory
                from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
                provider = ProviderFactory.create(config)
                assert isinstance(provider, AnthropicProvider)

    def test_creates_ollama_provider(self):
        config = self._make_config(provider="ollama")

        with patch("src.summarizer.llm.providers.ollama_provider._REQUESTS_AVAILABLE", True):
            from src.summarizer.llm.factory import ProviderFactory
            from src.summarizer.llm.providers.ollama_provider import OllamaProvider
            provider = ProviderFactory.create(config)
            assert isinstance(provider, OllamaProvider)

    def test_unsupported_provider_raises(self):
        config = self._make_config(provider="grok")
        from src.summarizer.llm.factory import ProviderFactory
        with pytest.raises(LLMError, match="Unsupported provider"):
            ProviderFactory.create(config)

    def test_ollama_uses_config_host(self):
        config = self._make_config(
            provider="ollama",
            ollama_host="http://myserver:11434",
            ollama_model="mistral",
        )
        with patch("src.summarizer.llm.providers.ollama_provider._REQUESTS_AVAILABLE", True):
            from src.summarizer.llm.factory import ProviderFactory
            provider = ProviderFactory.create(config)
            assert provider._host == "http://myserver:11434"
            assert provider._model == "mistral"

    def test_provider_name_case_insensitive(self):
        config = self._make_config(provider="OLLAMA")
        with patch("src.summarizer.llm.providers.ollama_provider._REQUESTS_AVAILABLE", True):
            from src.summarizer.llm.factory import ProviderFactory
            provider = ProviderFactory.create(config)
            assert provider.provider_name == "ollama"


# ─────────────────────────────────────────────────────────────────────────────
# Config Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSummarizerConfig:
    """Tests for SummarizerConfig validation."""

    def test_validate_openai_missing_key(self):
        from src.summarizer.config import SummarizerConfig
        config = SummarizerConfig()
        config.provider = "openai"
        config.openai_api_key = ""
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            config.validate()

    def test_validate_anthropic_missing_key(self):
        from src.summarizer.config import SummarizerConfig
        config = SummarizerConfig()
        config.provider = "anthropic"
        config.anthropic_api_key = ""
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            config.validate()

    def test_validate_ollama_no_key_required(self):
        from src.summarizer.config import SummarizerConfig
        config = SummarizerConfig()
        config.provider = "ollama"
        # Should not raise
        config.validate()

    def test_validate_unknown_provider(self):
        from src.summarizer.config import SummarizerConfig
        config = SummarizerConfig()
        config.provider = "grok"
        config.openai_api_key = "sk-test"
        with pytest.raises(ValueError, match="Unknown provider"):
            config.validate()

    def test_defaults_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-from-env")
        monkeypatch.setenv("OLLAMA_HOST", "http://custom:11434")

        from src.summarizer.config import SummarizerConfig
        config = SummarizerConfig.from_env()
        assert config.provider == "anthropic"
        assert config.anthropic_api_key == "ant-from-env"
        assert config.ollama_host == "http://custom:11434"