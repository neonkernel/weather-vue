"""Tests for multi-provider LLM support."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.summarizer.exceptions import LLMError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarize: The cat sat on the mat."},
]


# ---------------------------------------------------------------------------
# OpenAIProvider Tests
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    """Unit tests for OpenAIProvider."""

    def _make_provider(self, api_key: str = "sk-test", model: str | None = None):
        """Create an OpenAIProvider with a mocked openai client."""
        with patch("src.summarizer.llm.providers.openai_provider.OpenAI") as MockOpenAI:
            from src.summarizer.llm.providers.openai_provider import OpenAIProvider

            provider = OpenAIProvider(api_key=api_key, model=model)
            provider._client = MockOpenAI.return_value
            return provider

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "gpt-4o-mini"

    def test_complete_success(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "The cat is on a mat."
        provider._client.chat.completions.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "The cat is on a mat."
        provider._client.chat.completions.create.assert_called_once()

    def test_complete_uses_correct_model(self):
        provider = self._make_provider(model="gpt-4o")
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Summary."
        provider._client.chat.completions.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES)
        call_kwargs = provider._client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    def test_complete_model_override(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Summary."
        provider._client.chat.completions.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES, model="gpt-4-turbo")
        call_kwargs = provider._client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4-turbo"

    def test_complete_empty_response_raises(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        provider._client.chat.completions.create.return_value = mock_response

        with pytest.raises(LLMError, match="empty response"):
            provider.complete(SAMPLE_MESSAGES)

    def test_authentication_error_maps_to_llm_error(self):
        from openai import AuthenticationError as OAIAuthError
        provider = self._make_provider()

        mock_resp = MagicMock()
        mock_resp.request = MagicMock()
        provider._client.chat.completions.create.side_effect = (
            OAIAuthError("bad key", response=mock_resp, body={})
        )

        with pytest.raises(LLMError, match="authentication"):
            provider.complete(SAMPLE_MESSAGES)

    def test_rate_limit_error_maps_to_llm_error(self):
        from openai import RateLimitError as OAIRateLimitError
        provider = self._make_provider()

        mock_resp = MagicMock()
        mock_resp.request = MagicMock()
        provider._client.chat.completions.create.side_effect = (
            OAIRateLimitError("rate limit", response=mock_resp, body={})
        )

        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(SAMPLE_MESSAGES)

    def test_missing_api_key_raises(self):
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        with pytest.raises(LLMError, match="API key"):
            OpenAIProvider(api_key="")

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        provider._encoding = None  # force heuristic path
        count = provider.count_tokens("Hello world")
        assert count >= 1

    def test_count_tokens_tiktoken(self):
        provider = self._make_provider()
        if provider._encoding is not None:
            count = provider.count_tokens("Hello world")
            assert count > 0

    def test_complete_strips_whitespace(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "  Summary with spaces.  \n"
        provider._client.chat.completions.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Summary with spaces."


# ---------------------------------------------------------------------------
# AnthropicProvider Tests
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    """Unit tests for AnthropicProvider."""

    def _make_provider(self, api_key: str = "sk-ant-test", model: str | None = None):
        """Return an AnthropicProvider with anthropic SDK mocked."""
        anthropic_mock = MagicMock()
        anthropic_mock.AuthenticationError = type("AuthenticationError", (Exception,), {})
        anthropic_mock.RateLimitError = type("RateLimitError", (Exception,), {})
        anthropic_mock.APIStatusError = type(
            "APIStatusError", (Exception,), {"status_code": 500, "message": "err"}
        )
        anthropic_mock.APIConnectionError = type("APIConnectionError", (Exception,), {})

        with patch.dict("sys.modules", {"anthropic": anthropic_mock}):
            from importlib import reload
            import src.summarizer.llm.providers.anthropic_provider as mod
            reload(mod)
            provider = mod.AnthropicProvider(api_key=api_key, model=model)
            provider._anthropic = anthropic_mock
            provider._client = anthropic_mock.Anthropic.return_value
        return provider

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "claude-3-5-haiku-20241022"

    def test_complete_success(self):
        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = "A cat summary."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "A cat summary."

    def test_system_message_extracted(self):
        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = "result"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES)
        call_kwargs = provider._client.messages.create.call_args[1]

        # System prompt should be passed separately
        assert "system" in call_kwargs
        assert call_kwargs["system"] == "You are a helpful assistant."
        # messages list should only contain non-system messages
        for msg in call_kwargs["messages"]:
            assert msg["role"] != "system"

    def test_no_user_messages_raises(self):
        provider = self._make_provider()
        with pytest.raises(LLMError, match="No user"):
            provider.complete([{"role": "system", "content": "Only system."}])

    def test_empty_response_raises(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.content = []  # No blocks
        provider._client.messages.create.return_value = mock_response

        with pytest.raises(LLMError, match="empty response"):
            provider.complete(SAMPLE_MESSAGES)

    def test_authentication_error_maps(self):
        provider = self._make_provider()
        provider._client.messages.create.side_effect = (
            provider._anthropic.AuthenticationError("bad key")
        )
        with pytest.raises(LLMError, match="authentication"):
            provider.complete(SAMPLE_MESSAGES)

    def test_rate_limit_error_maps(self):
        provider = self._make_provider()
        provider._client.messages.create.side_effect = (
            provider._anthropic.RateLimitError("too many")
        )
        with pytest.raises(LLMError, match="rate limit"):
            provider.complete(SAMPLE_MESSAGES)

    def test_missing_api_key_raises(self):
        anthropic_mock = MagicMock()
        with patch.dict("sys.modules", {"anthropic": anthropic_mock}):
            from importlib import reload
            import src.summarizer.llm.providers.anthropic_provider as mod
            reload(mod)
            with pytest.raises(LLMError, match="API key"):
                mod.AnthropicProvider(api_key="")

    def test_count_tokens(self):
        provider = self._make_provider()
        assert provider.count_tokens("Hello world, this is a test.") >= 1

    def test_multiple_content_blocks_joined(self):
        provider = self._make_provider()
        block1 = MagicMock()
        block1.text = "Part one. "
        block2 = MagicMock()
        block2.text = "Part two."
        mock_response = MagicMock()
        mock_response.content = [block1, block2]
        provider._client.messages.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert "Part one." in result
        assert "Part two." in result

    def test_model_override_in_kwargs(self):
        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = "result"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES, model="claude-3-5-sonnet-20241022")
        call_kwargs = provider._client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"


# ---------------------------------------------------------------------------
# OllamaProvider Tests
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    """Unit tests for OllamaProvider."""

    def _make_provider(self, host: str = "http://localhost:11434", model: str | None = None):
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider(host=host, model=model)
        provider._requests = MagicMock()
        return provider

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "llama3"

    def test_complete_success(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "A cat summary."}
        }
        mock_response.raise_for_status = MagicMock()
        provider._requests.post.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "A cat summary."

    def test_complete_posts_to_correct_url(self):
        provider = self._make_provider(host="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "result"}
        }
        mock_response.raise_for_status = MagicMock()
        provider._requests.post.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES)
        call_args = provider._requests.post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"

    def test_complete_sends_messages(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "result"}
        }
        mock_response.raise_for_status = MagicMock()
        provider._requests.post.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES)
        payload = provider._requests.post.call_args[1]["json"]
        assert payload["messages"] == SAMPLE_MESSAGES
        assert payload["stream"] is False

    def test_complete_model_override(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "result"}
        }
        mock_response.raise_for_status = MagicMock()
        provider._requests.post.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES, model="mistral")
        payload = provider._requests.post.call_args[1]["json"]
        assert payload["model"] == "mistral"

    def test_empty_content_raises(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"role": "assistant", "content": ""}}
        mock_response.raise_for_status = MagicMock()
        provider._requests.post.return_value = mock_response

        with pytest.raises(LLMError, match="empty response"):
            provider.complete(SAMPLE_MESSAGES)

    def test_connection_error_maps(self):
        import requests as real_requests
        provider = self._make_provider()
        provider._requests.exceptions.ConnectionError = (
            real_requests.exceptions.ConnectionError
        )
        provider._requests.post.side_effect = real_requests.exceptions.ConnectionError()

        with pytest.raises(LLMError, match="Cannot connect"):
            provider.complete(SAMPLE_MESSAGES)

    def test_timeout_error_maps(self):
        import requests as real_requests
        provider = self._make_provider()
        provider._requests.exceptions.Timeout = real_requests.exceptions.Timeout
        provider._requests.exceptions.ConnectionError = (
            real_requests.exceptions.ConnectionError
        )
        provider._requests.post.side_effect = real_requests.exceptions.Timeout()

        with pytest.raises(LLMError, match="timed out"):
            provider.complete(SAMPLE_MESSAGES)

    def test_http_error_maps(self):
        import requests as real_requests
        provider = self._make_provider()
        provider._requests.exceptions.HTTPError = real_requests.exceptions.HTTPError
        provider._requests.exceptions.ConnectionError = (
            real_requests.exceptions.ConnectionError
        )
        provider._requests.exceptions.Timeout = real_requests.exceptions.Timeout

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"error": "model not found"}
        mock_resp.text = "model not found"
        http_error = real_requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_error
        provider._requests.post.return_value = mock_resp

        with pytest.raises(LLMError, match="404"):
            provider.complete(SAMPLE_MESSAGES)

    def test_list_models_success(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [{"name": "llama3"}, {"name": "mistral"}]
        }
        mock_response.raise_for_status = MagicMock()
        provider._requests.get.return_value = mock_response

        models = provider.list_models()
        assert "llama3" in models
        assert "mistral" in models

    def test_list_models_connection_error(self):
        import requests as real_requests
        provider = self._make_provider()
        provider._requests.exceptions.ConnectionError = (
            real_requests.exceptions.ConnectionError
        )
        provider._requests.exceptions.HTTPError = real_requests.exceptions.HTTPError
        provider._requests.get.side_effect = real_requests.exceptions.ConnectionError()

        with pytest.raises(LLMError, match="Cannot connect"):
            provider.list_models()

    def test_custom_host(self):
        provider = self._make_provider(host="http://192.168.1.100:11434")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "result"}
        }
        mock_response.raise_for_status = MagicMock()
        provider._requests.post.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES)
        call_args = provider._requests.post.call_args
        assert "192.168.1.100" in call_args[0][0]

    def test_count_tokens(self):
        provider = self._make_provider()
        assert provider.count_tokens("Hello world test string") >= 1


# ---------------------------------------------------------------------------
# ProviderFactory Tests
# ---------------------------------------------------------------------------


class TestProviderFactory:
    """Unit tests for ProviderFactory."""

    def _make_config(self, **kwargs: Any):
        from src.summarizer.config import Config

        defaults = {
            "provider": "openai",
            "openai_api_key": "sk-test",
            "anthropic_api_key": "sk-ant-test",
            "ollama_host": "http://localhost:11434",
            "model": None,
            "max_tokens": 4096,
            "temperature": 0.3,
        }
        defaults.update(kwargs)
        return Config(**defaults)

    def test_creates_openai_provider(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        config = self._make_config(provider="openai")
        with patch("src.summarizer.llm.providers.openai_provider.OpenAI"):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAIProvider)

    def test_creates_anthropic_provider(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider

        config = self._make_config(provider="anthropic")
        anthropic_mock = MagicMock()
        anthropic_mock.AuthenticationError = Exception
        anthropic_mock.RateLimitError = Exception
        anthropic_mock.APIStatusError = Exception
        anthropic_mock.APIConnectionError = Exception

        with patch.dict("sys.modules", {"anthropic": anthropic_mock}):
            from importlib import reload
            import src.summarizer.llm.providers.anthropic_provider as mod
            reload(mod)
            with patch(
                "src.summarizer.llm.factory.ProviderFactory._create_anthropic"
            ) as mock_create:
                mock_instance = MagicMock(spec=AnthropicProvider)
                mock_create.return_value = mock_instance
                result = ProviderFactory.create(config)
                assert result is mock_instance

    def test_creates_ollama_provider(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        config = self._make_config(provider="ollama")
        provider = ProviderFactory.create(config)
        assert isinstance(provider, OllamaProvider)

    def test_unknown_provider_raises(self):
        from src.summarizer.llm.factory import ProviderFactory

        config = self._make_config(provider="unknown_llm")
        with pytest.raises(LLMError, match="Unknown LLM provider"):
            ProviderFactory.create(config)

    def test_case_insensitive_provider_name(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        config = self._make_config(provider="OpenAI")
        with patch("src.summarizer.llm.providers.openai_provider.OpenAI"):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAIProvider)


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------


class TestConfig:
    """Tests for provider-related Config fields."""

    def test_default_provider_is_openai(self):
        from src.summarizer.config import Config

        config = Config()
        assert config.provider == "openai"

    def test_from_env_reads_llm_provider(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-123")

        from importlib import reload
        import src.summarizer.config as cfg_mod
        reload(cfg_mod)

        config = cfg_mod.Config.from_env()
        assert config.provider == "anthropic"
        assert config.anthropic_api_key == "sk-ant-123"

    def test_from_env_reads_ollama_host(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://mymachine:11434")

        from importlib import reload
        import src.summarizer.config as cfg_mod
        reload(cfg_mod)

        config = cfg_mod.Config.from_env()
        assert config.ollama_host == "http://mymachine:11434"

    def test_override_takes_precedence_over_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")

        from src.summarizer.config import Config

        config = Config.from_env(provider="ollama")
        assert config.provider == "ollama"

    def test_anthropic_api_key_field(self):
        from src.summarizer.config import Config

        config = Config(anthropic_api_key="sk-ant-xyz")
        assert config.anthropic_api_key == "sk-ant-xyz"

    def test_ollama_host_default(self):
        from src.summarizer.config import Config

        config = Config()
        assert config.ollama_host == "http://localhost:11434"


# ---------------------------------------------------------------------------
# CLI --provider flag Tests
# ---------------------------------------------------------------------------


class TestCLIProviderFlag:
    """Tests for the --provider CLI flag."""

    def test_provider_flag_openai(self):
        from src.summarizer.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["some_file.txt", "--provider", "openai"])
        assert args.provider == "openai"

    def test_provider_flag_anthropic(self):
        from src.summarizer.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["some_file.txt", "--provider", "anthropic"])
        assert args.provider == "anthropic"

    def test_provider_flag_ollama(self):
        from src.summarizer.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["some_file.txt", "--provider", "ollama"])
        assert args.provider == "ollama"

    def test_invalid_provider_rejected(self):
        from src.summarizer.cli import build_parser
        import io

        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["some_file.txt", "--provider", "invalid_provider"])

    def test_provider_default_is_none(self):
        """Default is None so env vars take effect in _build_config."""
        from src.summarizer.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["some_file.txt"])
        assert args.provider is None

    def test_list_models_flag(self):
        from src.summarizer.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["--provider", "ollama", "--list-models"])
        assert args.list_models is True

    def test_model_flag(self):
        from src.summarizer.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["file.txt", "--provider", "ollama", "--model", "mistral"])
        assert args.model == "mistral"