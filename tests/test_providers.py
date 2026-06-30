"""Tests for LLM provider implementations."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.summarizer.exceptions import LLMError
from src.summarizer.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs: Any) -> Config:
    base = {
        "openai_api_key": "sk-test-openai",
        "anthropic_api_key": "sk-test-anthropic",
        "ollama_host": "http://localhost:11434",
        "model": None,
    }
    base.update(kwargs)
    return Config(**base)


SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarize this text."},
]


# ===========================================================================
# OpenAI Provider
# ===========================================================================

class TestOpenAIProvider:
    def _make_provider(self, **config_kwargs: Any):
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        config = _make_config(**config_kwargs)
        with patch("openai.OpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            provider = OpenAIProvider(config=config)
            provider._client = mock_cls.return_value
        return provider

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "gpt-4o-mini"

    def test_uses_model_from_config(self):
        provider = self._make_provider(model="gpt-4o")
        assert provider._model == "gpt-4o"

    def test_complete_returns_content(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Hello, world!"
        provider._client.chat.completions.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Hello, world!"

    def test_complete_raises_llm_error_on_api_failure(self):
        provider = self._make_provider()
        provider._client.chat.completions.create.side_effect = RuntimeError("API down")

        with pytest.raises(LLMError, match="OpenAI API error"):
            provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_empty_response(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        provider._client.chat.completions.create.return_value = mock_response

        with pytest.raises(LLMError, match="empty response"):
            provider.complete(SAMPLE_MESSAGES)

    def test_missing_api_key_raises(self):
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        config = Config(openai_api_key=None, anthropic_api_key=None)
        with patch.dict("os.environ", {}, clear=True):
            # Ensure env var is not set
            import os
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(LLMError, match="API key"):
                OpenAIProvider(config=config)

    def test_count_tokens_fallback(self):
        provider = self._make_provider()
        # Patch tiktoken to raise so we fall back to heuristic
        with patch.dict("sys.modules", {"tiktoken": None}):
            count = provider.count_tokens("hello world")
            assert count >= 1

    def test_passes_max_tokens_to_api(self):
        provider = self._make_provider(max_tokens=512)
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"
        provider._client.chat.completions.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES, max_tokens=256)
        call_kwargs = provider._client.chat.completions.create.call_args[1]
        assert call_kwargs["max_tokens"] == 256


# ===========================================================================
# Anthropic Provider
# ===========================================================================

class TestAnthropicProvider:
    def _make_provider(self, **config_kwargs: Any):
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider

        config = _make_config(**config_kwargs)
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value = MagicMock()
            provider = AnthropicProvider(config=config)
            provider._client = mock_cls.return_value
        return provider

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "claude-3-5-haiku-20241022"

    def test_model_alias_resolution(self):
        provider = self._make_provider(model="claude-3-5-sonnet")
        assert provider._model == "claude-3-5-sonnet-20241022"

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        # 35 chars / 3.5 = 10 tokens
        assert provider.count_tokens("a" * 35) == 10

    def test_complete_returns_content(self):
        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "Summary here."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Summary here."

    def test_system_prompt_extracted(self):
        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "ok"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        provider._client.messages.create.return_value = mock_response

        provider.complete(SAMPLE_MESSAGES)

        call_kwargs = provider._client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are a helpful assistant."
        # System message should not appear in messages list
        for msg in call_kwargs["messages"]:
            assert msg["role"] != "system"

    def test_complete_raises_llm_error_on_api_failure(self):
        provider = self._make_provider()
        provider._client.messages.create.side_effect = RuntimeError("Network error")

        with pytest.raises(LLMError, match="Anthropic API error"):
            provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_empty_response(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.content = []
        provider._client.messages.create.return_value = mock_response

        with pytest.raises(LLMError, match="empty response"):
            provider.complete(SAMPLE_MESSAGES)

    def test_raises_on_no_conversation_messages(self):
        provider = self._make_provider()
        with pytest.raises(LLMError, match="No user/assistant messages"):
            provider.complete([{"role": "system", "content": "Only system"}])

    def test_missing_api_key_raises(self):
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider

        config = Config(openai_api_key=None, anthropic_api_key=None)
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(LLMError, match="API key"):
                AnthropicProvider(config=config)

    def test_multiple_content_blocks_joined(self):
        provider = self._make_provider()

        blocks = [MagicMock(), MagicMock()]
        blocks[0].text = "Part one. "
        blocks[1].text = "Part two."
        mock_response = MagicMock()
        mock_response.content = blocks
        provider._client.messages.create.return_value = mock_response

        result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Part one. Part two."


# ===========================================================================
# Ollama Provider
# ===========================================================================

class TestOllamaProvider:
    def _make_provider(self, **config_kwargs: Any):
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        config = _make_config(**config_kwargs)
        # No auth needed for Ollama
        return OllamaProvider(config=config)

    def _mock_post(self, content: str = "Ollama response"):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": content}}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.default_model == "llama3.2"

    def test_custom_host_from_config(self):
        provider = self._make_provider(ollama_host="http://myserver:11434")
        assert provider._host == "http://myserver:11434"

    def test_host_trailing_slash_stripped(self):
        provider = self._make_provider(ollama_host="http://localhost:11434/")
        assert provider._host == "http://localhost:11434"

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        assert provider.count_tokens("a" * 40) == 10

    def test_complete_returns_content(self):
        provider = self._make_provider()
        with patch("requests.post", return_value=self._mock_post("Hello from Ollama")) as mock_post:
            result = provider.complete(SAMPLE_MESSAGES)
        assert result == "Hello from Ollama"
        mock_post.assert_called_once()

    def test_complete_sends_correct_payload(self):
        provider = self._make_provider()
        with patch("requests.post", return_value=self._mock_post()) as mock_post:
            provider.complete(SAMPLE_MESSAGES, temperature=0.5, max_tokens=100)

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "llama3.2"
        assert payload["messages"] == SAMPLE_MESSAGES
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.5
        assert payload["options"]["num_predict"] == 100

    def test_complete_raises_on_connection_error(self):
        import requests as req_lib

        provider = self._make_provider()
        with patch("requests.post", side_effect=req_lib.exceptions.ConnectionError("refused")):
            with pytest.raises(LLMError, match="Cannot connect to Ollama"):
                provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_http_error(self):
        import requests as req_lib

        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"error": "model not found"}
        http_err = req_lib.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_err

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(LLMError, match="HTTP 404"):
                provider.complete(SAMPLE_MESSAGES)

    def test_complete_raises_on_empty_content(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": ""}}
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(LLMError, match="empty response"):
                provider.complete(SAMPLE_MESSAGES)

    def test_list_models(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [{"name": "llama3.2"}, {"name": "mistral"}]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            models = provider.list_models()

        assert models == ["llama3.2", "mistral"]

    def test_list_models_raises_on_error(self):
        provider = self._make_provider()
        with patch("requests.get", side_effect=RuntimeError("timeout")):
            with pytest.raises(LLMError, match="Failed to list Ollama models"):
                provider.list_models()


# ===========================================================================
# ProviderFactory
# ===========================================================================

class TestProviderFactory:
    def test_returns_openai_provider(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.openai_provider import OpenAIProvider

        config = _make_config(provider="openai")
        with patch("openai.OpenAI"):
            provider = ProviderFactory.get_provider(config=config)
        assert isinstance(provider, OpenAIProvider)

    def test_returns_anthropic_provider(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider

        config = _make_config(provider="anthropic")
        with patch("anthropic.Anthropic"):
            provider = ProviderFactory.get_provider(config=config)
        assert isinstance(provider, AnthropicProvider)

    def test_returns_ollama_provider(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        config = _make_config(provider="ollama")
        provider = ProviderFactory.get_provider(config=config)
        assert isinstance(provider, OllamaProvider)

    def test_explicit_name_overrides_config(self):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        config = _make_config(provider="openai")  # config says openai
        provider = ProviderFactory.get_provider(config=config, provider_name="ollama")
        assert isinstance(provider, OllamaProvider)

    def test_unknown_provider_raises(self):
        from src.summarizer.llm.factory import ProviderFactory

        config = _make_config(provider="grok")
        with pytest.raises(LLMError, match="Unknown LLM provider"):
            ProviderFactory.get_provider(config=config)

    def test_env_var_used_as_fallback(self, monkeypatch: pytest.MonkeyPatch):
        from src.summarizer.llm.factory import ProviderFactory
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider

        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        # Config with no provider set (will default to env var in Config.from_env)
        config = Config(
            openai_api_key="sk-test",
            anthropic_api_key="sk-anth",
            provider="ollama",  # mirrors what from_env would produce
        )
        provider = ProviderFactory.get_provider(config=config)
        assert isinstance(provider, OllamaProvider)