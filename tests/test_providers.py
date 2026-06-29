"""Tests for LLM provider implementations."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.summarizer.exceptions import LLMError


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_config(**overrides):
    """Return a minimal config-like namespace."""
    defaults = dict(
        provider="openai",
        model=None,
        temperature=0.3,
        max_tokens=1024,
        openai_api_key="sk-test-openai",
        anthropic_api_key="sk-ant-test",
        ollama_host="http://localhost:11434",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    def _make_provider(self, **kwargs):
        config = make_config(**kwargs)
        with patch("openai.OpenAI"):
            from src.summarizer.llm.providers.openai_provider import OpenAIProvider
            return OpenAIProvider(config)

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "openai"

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "gpt-4o-mini"

    def test_model_from_config(self):
        provider = self._make_provider(model="gpt-4o")
        assert provider._model == "gpt-4o"

    def test_missing_api_key_raises(self):
        config = make_config(openai_api_key=None)
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMError, match="API key"):
                with patch("openai.OpenAI"):
                    from src.summarizer.llm.providers.openai_provider import OpenAIProvider
                    OpenAIProvider(config)

    def test_complete_returns_content(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Summary text"
        provider._client.chat.completions.create.return_value = mock_response

        result = provider.complete([{"role": "user", "content": "Summarize this."}])
        assert result == "Summary text"

    def test_complete_passes_temperature_and_max_tokens(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"
        provider._client.chat.completions.create.return_value = mock_response

        provider.complete(
            [{"role": "user", "content": "hi"}],
            temperature=0.7,
            max_tokens=512,
        )
        call_kwargs = provider._client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 512

    def test_complete_model_override(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"
        provider._client.chat.completions.create.return_value = mock_response

        provider.complete([{"role": "user", "content": "hi"}], model="gpt-4o")
        call_kwargs = provider._client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    def test_auth_error_maps_to_llm_error(self):
        import openai

        provider = self._make_provider()
        provider._client.chat.completions.create.side_effect = openai.AuthenticationError(
            "bad key", response=MagicMock(status_code=401), body={}
        )
        with pytest.raises(LLMError, match="authentication"):
            provider.complete([{"role": "user", "content": "hi"}])

    def test_rate_limit_maps_to_llm_error(self):
        import openai

        provider = self._make_provider()
        provider._client.chat.completions.create.side_effect = openai.RateLimitError(
            "rate limited", response=MagicMock(status_code=429), body={}
        )
        with pytest.raises(LLMError, match="rate limit"):
            provider.complete([{"role": "user", "content": "hi"}])

    def test_count_tokens_without_tiktoken(self):
        provider = self._make_provider()
        provider._encoding = None  # Simulate missing tiktoken
        count = provider.count_tokens("Hello world")
        assert count >= 1

    def test_count_tokens_with_tiktoken(self):
        provider = self._make_provider()
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [1, 2, 3]
        provider._encoding = mock_enc
        assert provider.count_tokens("Hello world") == 3

    def test_empty_response_raises(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        provider._client.chat.completions.create.return_value = mock_response

        with pytest.raises(LLMError, match="empty"):
            provider.complete([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# Anthropic Provider
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    def _make_provider(self, **kwargs):
        config = make_config(**kwargs)
        with patch("anthropic.Anthropic"):
            from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(config)
        return provider

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "anthropic"

    def test_default_model(self):
        provider = self._make_provider()
        assert "claude" in provider.default_model

    def test_model_alias_resolution(self):
        from src.summarizer.llm.providers.anthropic_provider import _resolve_model
        assert _resolve_model("claude-3-5-haiku") == "claude-3-5-haiku-20241022"
        assert _resolve_model("claude-3-opus") == "claude-3-opus-20240229"
        # Unknown names pass through unchanged
        assert _resolve_model("my-custom-model") == "my-custom-model"

    def test_missing_api_key_raises(self):
        config = make_config(anthropic_api_key=None)
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMError, match="API key"):
                with patch("anthropic.Anthropic"):
                    from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
                    AnthropicProvider(config)

    def test_complete_extracts_text_blocks(self):
        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "Claude summary"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        result = provider.complete([{"role": "user", "content": "Summarize this."}])
        assert result == "Claude summary"

    def test_system_message_extracted(self):
        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "ok"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        provider.complete(messages)

        call_kwargs = provider._client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful."
        # system message removed from messages list
        for msg in call_kwargs["messages"]:
            assert msg["role"] != "system"

    def test_no_system_message_no_system_kwarg(self):
        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "ok"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        provider.complete([{"role": "user", "content": "Hello"}])
        call_kwargs = provider._client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_auth_error_maps_to_llm_error(self):
        provider = self._make_provider()
        mock_exc = MagicMock(spec=Exception)
        mock_exc.__class__ = provider._anthropic.AuthenticationError

        provider._client.messages.create.side_effect = \
            provider._anthropic.AuthenticationError("bad key")
        with pytest.raises(LLMError, match="authentication"):
            provider.complete([{"role": "user", "content": "hi"}])

    def test_rate_limit_maps_to_llm_error(self):
        provider = self._make_provider()
        provider._client.messages.create.side_effect = \
            provider._anthropic.RateLimitError("too many")
        with pytest.raises(LLMError, match="rate limit"):
            provider.complete([{"role": "user", "content": "hi"}])

    def test_empty_content_raises(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.content = []
        provider._client.messages.create.return_value = mock_response

        with pytest.raises(LLMError, match="empty"):
            provider.complete([{"role": "user", "content": "hi"}])

    def test_count_tokens(self):
        provider = self._make_provider()
        count = provider.count_tokens("Hello world, this is a test.")
        assert count >= 1

    def test_multiple_text_blocks_concatenated(self):
        provider = self._make_provider()

        block1, block2 = MagicMock(), MagicMock()
        block1.text = "Part one. "
        block2.text = "Part two."
        mock_response = MagicMock()
        mock_response.content = [block1, block2]
        provider._client.messages.create.return_value = mock_response

        result = provider.complete([{"role": "user", "content": "hi"}])
        assert result == "Part one. Part two."


# ---------------------------------------------------------------------------
# Ollama Provider
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    def _make_provider(self, **kwargs):
        config = make_config(**kwargs)
        with patch("requests.post"), patch("requests.get"):
            from src.summarizer.llm.providers.ollama_provider import OllamaProvider
            return OllamaProvider(config)

    def _mock_response(self, content: str, status_code: int = 200) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = {
            "message": {"role": "assistant", "content": content}
        }
        mock_resp.text = json.dumps(mock_resp.json.return_value)
        return mock_resp

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.provider_name == "ollama"

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "llama3.2"

    def test_default_host(self):
        provider = self._make_provider()
        assert "localhost:11434" in provider._host

    def test_custom_host_from_config(self):
        provider = self._make_provider(ollama_host="http://myserver:11434")
        assert provider._host == "http://myserver:11434"

    def test_complete_returns_content(self):
        provider = self._make_provider()
        mock_resp = self._mock_response("Ollama summary")

        with patch.object(provider._requests, "post", return_value=mock_resp):
            result = provider.complete([{"role": "user", "content": "Summarize."}])

        assert result == "Ollama summary"

    def test_complete_sends_correct_payload(self):
        provider = self._make_provider()
        mock_resp = self._mock_response("ok")

        with patch.object(provider._requests, "post", return_value=mock_resp) as mock_post:
            provider.complete(
                [{"role": "user", "content": "hi"}],
                temperature=0.5,
                max_tokens=256,
            )

        payload = mock_post.call_args[1]["json"]
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.5
        assert payload["options"]["num_predict"] == 256

    def test_model_override(self):
        provider = self._make_provider()
        mock_resp = self._mock_response("ok")

        with patch.object(provider._requests, "post", return_value=mock_resp) as mock_post:
            provider.complete([{"role": "user", "content": "hi"}], model="mistral")

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "mistral"

    def test_connection_error_maps_to_llm_error(self):
        import requests

        provider = self._make_provider()
        with patch.object(
            provider._requests,
            "post",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(LLMError, match="connect"):
                provider.complete([{"role": "user", "content": "hi"}])

    def test_timeout_maps_to_llm_error(self):
        import requests

        provider = self._make_provider()
        with patch.object(
            provider._requests,
            "post",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(LLMError, match="timed out"):
                provider.complete([{"role": "user", "content": "hi"}])

    def test_404_model_not_found(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "model not found"

        with patch.object(provider._requests, "post", return_value=mock_resp):
            with pytest.raises(LLMError, match="not found"):
                provider.complete([{"role": "user", "content": "hi"}])

    def test_500_server_error(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "internal error"

        with patch.object(provider._requests, "post", return_value=mock_resp):
            with pytest.raises(LLMError, match="internal server error"):
                provider.complete([{"role": "user", "content": "hi"}])

    def test_empty_content_raises(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"role": "assistant", "content": ""}}

        with patch.object(provider._requests, "post", return_value=mock_resp):
            with pytest.raises(LLMError, match="empty"):
                provider.complete([{"role": "user", "content": "hi"}])

    def test_malformed_json_raises(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "not json"

        with patch.object(provider._requests, "post", return_value=mock_resp):
            with pytest.raises(LLMError, match="non-JSON"):
                provider.complete([{"role": "user", "content": "hi"}])

    def test_list_models(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [{"name": "llama3.2"}, {"name": "mistral"}]
        }
        mock_resp.raise_for_status.return_value = None

        with patch.object(provider._requests, "get", return_value=mock_resp):
            models = provider.list_models()

        assert "llama3.2" in models
        assert "mistral" in models

    def test_count_tokens(self):
        provider = self._make_provider()
        count = provider.count_tokens("Hello world")
        assert count >= 1


# ---------------------------------------------------------------------------
# ProviderFactory
# ---------------------------------------------------------------------------


class TestProviderFactory:
    def test_create_openai(self):
        from src.summarizer.llm.factory import ProviderFactory

        config = make_config(provider="openai")
        with patch("openai.OpenAI"):
            provider = ProviderFactory.create("openai", config)
        assert provider.provider_name == "openai"

    def test_create_anthropic(self):
        from src.summarizer.llm.factory import ProviderFactory

        config = make_config(provider="anthropic")
        with patch("anthropic.Anthropic"):
            provider = ProviderFactory.create("anthropic", config)
        assert provider.provider_name == "anthropic"

    def test_create_ollama(self):
        from src.summarizer.llm.factory import ProviderFactory

        config = make_config(provider="ollama")
        provider = ProviderFactory.create("ollama", config)
        assert provider.provider_name == "ollama"

    def test_unknown_provider_raises(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.exceptions import LLMError

        config = make_config()
        with pytest.raises(LLMError, match="Unknown provider"):
            ProviderFactory.create("nonexistent", config)

    def test_from_config_reads_provider_field(self):
        from src.summarizer.llm.factory import ProviderFactory

        config = make_config(provider="ollama")
        provider = ProviderFactory.from_config(config)
        assert provider.provider_name == "ollama"

    def test_from_config_env_fallback(self):
        from src.summarizer.llm.factory import ProviderFactory

        config = make_config(provider=None)
        with patch.dict("os.environ", {"LLM_PROVIDER": "ollama"}):
            provider = ProviderFactory.from_config(config)
        assert provider.provider_name == "ollama"

    def test_case_insensitive(self):
        from src.summarizer.llm.factory import ProviderFactory

        config = make_config(provider="OPENAI")
        with patch("openai.OpenAI"):
            provider = ProviderFactory.create("OPENAI", config)
        assert provider.provider_name == "openai"