"""Tests for LLM provider implementations."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider
from src.summarizer.llm.factory import ProviderFactory


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarize this text."},
]


def make_openai_config(**kwargs) -> Config:
    defaults = dict(
        provider="openai",
        openai_api_key="sk-test-openai-key",
        openai_model="gpt-4o-mini",
    )
    defaults.update(kwargs)
    return Config(**defaults)


def make_anthropic_config(**kwargs) -> Config:
    defaults = dict(
        provider="anthropic",
        anthropic_api_key="sk-ant-test-key",
        anthropic_model="claude-3-5-haiku-20241022",
    )
    defaults.update(kwargs)
    return Config(**defaults)


def make_ollama_config(**kwargs) -> Config:
    defaults = dict(
        provider="ollama",
        ollama_host="http://localhost:11434",
        ollama_model="llama3.2",
    )
    defaults.update(kwargs)
    return Config(**defaults)


# ---------------------------------------------------------------------------
# BaseLLMProvider ABC
# ---------------------------------------------------------------------------

class TestBaseLLMProvider:
    def test_cannot_instantiate_directly(self):
        """BaseLLMProvider is an ABC and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMProvider()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_all_methods(self):
        """A partial implementation should raise TypeError on instantiation."""
        class PartialProvider(BaseLLMProvider):
            @property
            def provider_name(self):
                return "partial"
            # Missing: complete, count_tokens, default_model

        with pytest.raises(TypeError):
            PartialProvider()  # type: ignore[abstract]

    def test_valid_concrete_subclass(self):
        """A fully implemented subclass can be instantiated."""
        class MinimalProvider(BaseLLMProvider):
            @property
            def provider_name(self):
                return "minimal"

            @property
            def default_model(self):
                return "tiny-model"

            def complete(self, messages, **kwargs):
                return "summary"

            def count_tokens(self, text):
                return len(text.split())

        provider = MinimalProvider()
        assert provider.provider_name == "minimal"
        assert provider.default_model == "tiny-model"
        assert provider.complete([]) == "summary"
        assert provider.count_tokens("hello world") == 2


# ---------------------------------------------------------------------------
# ProviderFactory
# ---------------------------------------------------------------------------

class TestProviderFactory:
    def test_available_providers(self):
        providers = ProviderFactory.available_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_unknown_provider_raises_llm_error(self):
        with pytest.raises(LLMError, match="Unknown LLM provider"):
            ProviderFactory.create(provider_name="nonexistent")

    def test_resolves_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
        provider = ProviderFactory.create()
        assert provider.provider_name == "ollama"

    def test_explicit_name_overrides_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch("openai.OpenAI"):
            provider = ProviderFactory.create(provider_name="openai")
        assert provider.provider_name == "openai"

    def test_provider_name_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch("openai.OpenAI"):
            provider = ProviderFactory.create(provider_name="OpenAI")
        assert provider.provider_name == "openai"


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def _make_provider(self, **config_kwargs):
        config = make_openai_config(**config_kwargs)
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_openai_cls.return_value = MagicMock()
            from src.summarizer.llm.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider(config=config)
            provider._client = mock_openai_cls.return_value
        return provider

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "openai"

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "gpt-4o-mini"

    def test_model_from_config(self):
        provider = self._make_provider(openai_model="gpt-4o")
        assert provider._model == "gpt-4o"

    def test_complete_returns_content(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Great summary!"
        provider._client.chat.completions.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Great summary!"

    def test_complete_passes_messages(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"
        provider._client.chat.completions.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES, temperature=0.5)
        call_kwargs = provider._client.chat.completions.create.call_args
        assert call_kwargs.kwargs["messages"] == SAMPLE_MESSAGES
        assert call_kwargs.kwargs["temperature"] == 0.5

    def test_complete_allows_model_override(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"
        provider._client.chat.completions.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES, model="gpt-4o")
        call_kwargs = provider._client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o"

    def test_missing_api_key_raises_llm_error(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider
        config = Config(provider="openai", openai_api_key=None, openai_model="gpt-4o-mini")
        with pytest.raises(LLMError, match="OpenAI API key not found"):
            OpenAIProvider(config=config)

    def test_auth_error_mapped_to_llm_error(self):
        provider = self._make_provider()
        import openai
        provider._client.chat.completions.create.side_effect = openai.AuthenticationError(
            "Invalid API key", response=MagicMock(status_code=401), body={}
        )
        with pytest.raises(LLMError, match="authentication failed"):
            provider.complete(SAMPLE_MESSAGES)

    def test_rate_limit_error_mapped(self):
        provider = self._make_provider()
        import openai
        provider._client.chat.completions.create.side_effect = openai.RateLimitError(
            "Rate limit", response=MagicMock(status_code=429), body={}
        )
        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(SAMPLE_MESSAGES)

    def test_count_tokens_returns_int(self):
        provider = self._make_provider()
        count = provider.count_tokens("Hello, world! This is a test.")
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_longer_text_is_more(self):
        provider = self._make_provider()
        short = provider.count_tokens("Hi")
        long = provider.count_tokens("This is a much longer piece of text with many words.")
        assert long > short

    def test_empty_response_returns_empty_string(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        provider._client.chat.completions.create.return_value = mock_response
        result = provider.complete(SAMPLE_MESSAGES)
        assert result == ""


# ---------------------------------------------------------------------------
# Anthropic Provider
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def _make_provider(self, **config_kwargs):
        config = make_anthropic_config(**config_kwargs)
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value = MagicMock()
            from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(config=config)
            provider._client = mock_cls.return_value
        return provider

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "anthropic"

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "claude-3-5-haiku-20241022"

    def test_model_from_config(self):
        provider = self._make_provider(anthropic_model="claude-opus-4-5")
        assert provider._model == "claude-opus-4-5"

    def _make_mock_response(self, text: str) -> MagicMock:
        block = MagicMock()
        block.text = text
        response = MagicMock()
        response.content = [block]
        return response

    def test_complete_returns_text(self):
        provider = self._make_provider()
        provider._client.messages.create.return_value = self._make_mock_response("Claude summary")
        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Claude summary"

    def test_system_message_extracted(self):
        provider = self._make_provider()
        provider._client.messages.create.return_value = self._make_mock_response("ok")
        provider.complete(SAMPLE_MESSAGES)

        call_kwargs = provider._client.messages.create.call_args.kwargs
        # System message should be passed as top-level 'system' param
        assert "system" in call_kwargs
        assert "You are a helpful assistant" in call_kwargs["system"]
        # messages list should only contain user message
        assert all(m["role"] != "system" for m in call_kwargs["messages"])

    def test_messages_without_system(self):
        provider = self._make_provider()
        provider._client.messages.create.return_value = self._make_mock_response("ok")
        user_only = [{"role": "user", "content": "Hello"}]
        provider.complete(user_only)
        call_kwargs = provider._client.messages.create.call_args.kwargs
        assert "system" not in call_kwargs

    def test_model_override(self):
        provider = self._make_provider()
        provider._client.messages.create.return_value = self._make_mock_response("ok")
        provider.complete(SAMPLE_MESSAGES, model="claude-opus-4-5")
        call_kwargs = provider._client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-opus-4-5"

    def test_missing_api_key_raises_llm_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
        config = Config(provider="anthropic", anthropic_api_key=None)
        with pytest.raises(LLMError, match="Anthropic API key not found"):
            AnthropicProvider(config=config)

    def test_empty_messages_raises_llm_error(self):
        provider = self._make_provider()
        with pytest.raises(LLMError, match="at least one non-system message"):
            provider.complete([{"role": "system", "content": "Only system"}])

    def test_auth_error_mapped(self):
        provider = self._make_provider()
        import anthropic
        provider._client.messages.create.side_effect = anthropic.AuthenticationError(
            message="Bad key", response=MagicMock(status_code=401), body={}
        )
        with pytest.raises(LLMError, match="authentication failed"):
            provider.complete(SAMPLE_MESSAGES)

    def test_rate_limit_error_mapped(self):
        provider = self._make_provider()
        import anthropic
        provider._client.messages.create.side_effect = anthropic.RateLimitError(
            message="Too many requests",
            response=MagicMock(status_code=429),
            body={},
        )
        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(SAMPLE_MESSAGES)

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        count = provider.count_tokens("Hello world")
        assert isinstance(count, int)
        assert count >= 1

    def test_count_tokens_proportional(self):
        provider = self._make_provider()
        short = provider.count_tokens("Hi")
        long = provider.count_tokens("This is a significantly longer text with many more words in it.")
        assert long > short

    def test_multiple_content_blocks_joined(self):
        provider = self._make_provider()
        block1 = MagicMock()
        block1.text = "Part one."
        block2 = MagicMock()
        block2.text = "Part two."
        response = MagicMock()
        response.content = [block1, block2]
        provider._client.messages.create.return_value = response
        result = provider.complete(SAMPLE_MESSAGES)
        assert "Part one." in result
        assert "Part two." in result


# ---------------------------------------------------------------------------
# Ollama Provider
# ---------------------------------------------------------------------------

class TestOllamaProvider:
    """Tests for OllamaProvider using mocked HTTP responses."""

    def _make_provider(self, **config_kwargs):
        config = make_ollama_config(**config_kwargs)
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider
        return OllamaProvider(config=config)

    def _make_response(self, content: str, status_code: int = 200) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = {"message": {"content": content}}
        resp.text = content
        return resp

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "ollama"

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "llama3.2"

    def test_model_from_config(self):
        provider = self._make_provider(ollama_model="mistral")
        assert provider._model == "mistral"

    def test_host_from_config(self):
        provider = self._make_provider(ollama_host="http://192.168.1.100:11434")
        assert provider._host == "http://192.168.1.100:11434"

    def test_complete_returns_content(self):
        provider = self._make_provider()
        with patch("requests.post") as mock_post:
            mock_post.return_value = self._make_response("Ollama summary")
            result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Ollama summary"

    def test_complete_sends_correct_payload(self):
        provider = self._make_provider()
        with patch("requests.post") as mock_post:
            mock_post.return_value = self._make_response("ok")
            provider.complete(SAMPLE_MESSAGES, temperature=0.7, max_tokens=512)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
        assert payload["model"] == "llama3.2"
        assert payload["messages"] == SAMPLE_MESSAGES
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.7
        assert payload["options"]["num_predict"] == 512

    def test_complete_with_model_override(self):
        provider = self._make_provider()
        with patch("requests.post") as mock_post:
            mock_post.return_value = self._make_response("ok")
            provider.complete(SAMPLE_MESSAGES, model="mistral")
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args.args[1]
        assert payload["model"] == "mistral"

    def test_404_raises_llm_error_with_hint(self):
        provider = self._make_provider()
        with patch("requests.post") as mock_post:
            mock_post.return_value = self._make_response("not found", status_code=404)
            with pytest.raises(LLMError, match="ollama pull"):
                provider.complete(SAMPLE_MESSAGES)

    def test_500_raises_llm_error(self):
        provider = self._make_provider()
        resp = MagicMock()
        resp.status_code = 500
        resp.json.return_value = {"error": "CUDA out of memory"}
        resp.text = "CUDA out of memory"
        with patch("requests.post") as mock_post:
            mock_post.return_value = resp
            with pytest.raises(LLMError, match="server error"):
                provider.complete(SAMPLE_MESSAGES)

    def test_connection_error_mapped(self):
        provider = self._make_provider()
        import requests as req_lib
        with patch("requests.post", side_effect=req_lib.ConnectionError("refused")):
            with pytest.raises(LLMError, match="Cannot connect to Ollama"):
                provider.complete(SAMPLE_MESSAGES)

    def test_timeout_error_mapped(self):
        provider = self._make_provider()
        import requests as req_lib
        with patch("requests.post", side_effect=req_lib.Timeout("timed out")):
            with pytest.raises(LLMError, match="timed out"):
                provider.complete(SAMPLE_MESSAGES)

    def test_list_models_returns_names(self):
        provider = self._make_provider()
        tags_resp = MagicMock()
        tags_resp.status_code = 200
        tags_resp.json.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
                {"name": "codellama"},
            ]
        }
        with patch("requests.get", return_value=tags_resp):
            models = provider.list_models()
        assert models == ["llama3.2", "mistral", "codellama"]

    def test_list_models_empty(self):
        provider = self._make_provider()
        tags_resp = MagicMock()
        tags_resp.status_code = 200
        tags_resp.json.return_value = {"models": []}
        with patch("requests.get", return_value=tags_resp):
            models = provider.list_models()
        assert models == []

    def test_is_available_true(self):
        provider = self._make_provider()
        resp = MagicMock()
        resp.status_code = 200
        with patch("requests.get", return_value=resp):
            assert provider.is_available() is True

    def test_is_available_false_on_error(self):
        provider = self._make_provider()
        import requests as req_lib
        with patch("requests.get", side_effect=req_lib.ConnectionError()):
            assert provider.is_available() is False

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        count = provider.count_tokens("Hello world test")
        assert isinstance(count, int)
        assert count >= 1

    def test_count_tokens_minimum_one(self):
        provider = self._make_provider()
        # Even empty-ish string returns at least 1
        count = provider.count_tokens("ab")
        assert count >= 1


# ---------------------------------------------------------------------------
# Cross-provider: error mapping
# ---------------------------------------------------------------------------

class TestErrorMapping:
    """Verify error mapping produces LLMError with meaningful messages."""

    def test_openai_generic_error_wrapped(self):
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider
        err = OpenAIProvider._map_error(ValueError("some generic error"))
        assert isinstance(err, LLMError)
        assert "generic error" in str(err).lower() or "openai" in str(err).lower()

    def test_anthropic_generic_error_wrapped(self):
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
        err = AnthropicProvider._map_error(ValueError("some generic error"))
        assert isinstance(err, LLMError)

    def test_ollama_generic_error_wrapped(self):
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider
        err = OllamaProvider._map_error(ValueError("some generic error"))
        assert isinstance(err, LLMError)


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------

class TestConfigIntegration:
    def test_config_defaults(self):
        config = Config()
        assert config.provider in ("openai", "anthropic", "ollama")
        assert config.max_chunk_tokens > 0
        assert config.max_output_tokens > 0

    def test_config_provider_normalized(self):
        config = Config(provider="  OpenAI  ")
        assert config.provider == "openai"

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        config = Config.from_env()
        assert config.provider == "anthropic"
        assert config.anthropic_api_key == "sk-ant-test"

    def test_config_ollama_host_trailing_slash_stripped(self):
        config = Config(ollama_host="http://localhost:11434/")
        assert not config.ollama_host.endswith("/")