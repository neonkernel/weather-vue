"""Tests for LLM provider implementations."""

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.summarizer.config import Config
from src.summarizer.exceptions import LLMError
from src.summarizer.llm.factory import ProviderFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(**kwargs) -> Config:
    """Create a Config with sensible test defaults, overridden by kwargs."""
    defaults = dict(
        provider="openai",
        openai_api_key="sk-test-openai",
        anthropic_api_key="sk-ant-test",
        ollama_host="http://localhost:11434",
        model=None,
        max_tokens=512,
        temperature=0.0,
    )
    defaults.update(kwargs)
    return Config(**defaults)


# ---------------------------------------------------------------------------
# ProviderFactory tests
# ---------------------------------------------------------------------------

class TestProviderFactory:
    def test_available_providers(self):
        providers = ProviderFactory.available_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_unknown_provider_raises(self):
        config = make_config(provider="unknown_llm")
        with pytest.raises(LLMError, match="Unknown provider"):
            ProviderFactory.create(config)

    def test_creates_openai_provider(self):
        config = make_config(provider="openai")
        with patch("openai.OpenAI"):
            from src.summarizer.llm.providers.openai_provider import OpenAIProvider
            with patch.object(OpenAIProvider, "__init__", return_value=None):
                provider = ProviderFactory.create(config)
                assert isinstance(provider, OpenAIProvider)

    def test_creates_anthropic_provider(self):
        config = make_config(provider="anthropic")
        with patch("anthropic.Anthropic"):
            from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
            with patch.object(AnthropicProvider, "__init__", return_value=None):
                provider = ProviderFactory.create(config)
                assert isinstance(provider, AnthropicProvider)

    def test_creates_ollama_provider(self):
        config = make_config(provider="ollama")
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider
        with patch.object(OllamaProvider, "__init__", return_value=None):
            provider = ProviderFactory.create(config)
            assert isinstance(provider, OllamaProvider)


# ---------------------------------------------------------------------------
# OpenAI Provider tests
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    """Tests for OpenAIProvider using mocked openai SDK."""

    def _make_provider(self, config=None):
        if config is None:
            config = make_config(provider="openai")
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        with patch.dict("sys.modules", {"openai": mock_openai}):
            from src.summarizer.llm.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider.__new__(OpenAIProvider)
            provider.config = config
            provider.api_key = config.openai_api_key
            provider._openai = mock_openai
            provider._client = mock_client
            return provider, mock_openai, mock_client

    def test_get_default_model_no_config_model(self):
        provider, _, _ = self._make_provider()
        assert provider.get_default_model() == "gpt-4o-mini"

    def test_get_default_model_from_config(self):
        config = make_config(model="gpt-4o")
        provider, _, _ = self._make_provider(config)
        assert provider.get_default_model() == "gpt-4o"

    def test_complete_returns_content(self):
        provider, mock_openai, mock_client = self._make_provider()

        mock_message = MagicMock()
        mock_message.content = "Test summary"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a summarizer."},
            {"role": "user", "content": "Summarize this."},
        ]
        result = provider.complete(messages)
        assert result == "Test summary"
        mock_client.chat.completions.create.assert_called_once()

    def test_complete_uses_kwargs_model(self):
        provider, _, mock_client = self._make_provider()

        mock_message = MagicMock()
        mock_message.content = "ok"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response

        provider.complete([{"role": "user", "content": "hi"}], model="gpt-4o")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    def test_complete_maps_auth_error(self):
        provider, mock_openai, mock_client = self._make_provider()
        mock_openai.AuthenticationError = type("AuthenticationError", (Exception,), {})
        mock_client.chat.completions.create.side_effect = mock_openai.AuthenticationError("bad key")

        with pytest.raises(LLMError, match="authentication failed"):
            provider.complete([{"role": "user", "content": "test"}])

    def test_complete_maps_rate_limit_error(self):
        provider, mock_openai, mock_client = self._make_provider()
        mock_openai.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_client.chat.completions.create.side_effect = mock_openai.RateLimitError("429")

        with pytest.raises(LLMError, match="rate limit"):
            provider.complete([{"role": "user", "content": "test"}])

    def test_no_api_key_raises(self):
        config = make_config(openai_api_key="")
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            from src.summarizer.llm.providers.openai_provider import OpenAIProvider
            import importlib
            import src.summarizer.llm.providers.openai_provider as mod
            importlib.reload(mod)
            with patch("os.environ.get", return_value=""):
                with pytest.raises(LLMError, match="API key not found"):
                    mod.OpenAIProvider(config)

    def test_count_tokens_fallback(self):
        provider, _, _ = self._make_provider()
        # Without tiktoken, falls back to len//4
        with patch.dict("sys.modules", {"tiktoken": None}):
            count = provider.count_tokens("hello world test")
            assert isinstance(count, int)
            assert count >= 1


# ---------------------------------------------------------------------------
# Anthropic Provider tests
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    """Tests for AnthropicProvider using mocked anthropic SDK."""

    def _make_provider(self, config=None):
        if config is None:
            config = make_config(provider="anthropic")
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        provider = MagicMock()

        from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
        p = AnthropicProvider.__new__(AnthropicProvider)
        p.config = config
        p.api_key = config.anthropic_api_key
        p._anthropic = mock_anthropic
        p._client = mock_client
        return p, mock_anthropic, mock_client

    def test_get_default_model(self):
        provider, _, _ = self._make_provider()
        model = provider.get_default_model()
        assert "claude" in model

    def test_get_default_model_alias_expansion(self):
        config = make_config(model="claude-3-5-sonnet")
        provider, _, _ = self._make_provider(config)
        assert provider.get_default_model() == "claude-3-5-sonnet-20241022"

    def test_complete_extracts_system_message(self):
        provider, mock_anthropic, mock_client = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "Summary text"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "You summarize things."},
            {"role": "user", "content": "Summarize this document."},
        ]
        result = provider.complete(messages)
        assert result == "Summary text"

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You summarize things."
        # system role should not appear in messages list
        for msg in call_kwargs["messages"]:
            assert msg["role"] != "system"

    def test_complete_no_system_message(self):
        provider, _, mock_client = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = "Result"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        result = provider.complete(messages)
        assert result == "Result"

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_complete_concatenates_text_blocks(self):
        provider, _, mock_client = self._make_provider()

        block1 = MagicMock()
        block1.text = "Part one. "
        block2 = MagicMock()
        block2.text = "Part two."
        mock_response = MagicMock()
        mock_response.content = [block1, block2]
        mock_client.messages.create.return_value = mock_response

        result = provider.complete([{"role": "user", "content": "hi"}])
        assert result == "Part one. Part two."

    def test_maps_auth_error(self):
        provider, mock_anthropic, mock_client = self._make_provider()
        mock_anthropic.AuthenticationError = type("AuthenticationError", (Exception,), {})
        mock_client.messages.create.side_effect = mock_anthropic.AuthenticationError("bad key")

        with pytest.raises(LLMError, match="authentication failed"):
            provider.complete([{"role": "user", "content": "test"}])

    def test_maps_rate_limit_error(self):
        provider, mock_anthropic, mock_client = self._make_provider()
        mock_anthropic.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_client.messages.create.side_effect = mock_anthropic.RateLimitError("429")

        with pytest.raises(LLMError, match="rate limit"):
            provider.complete([{"role": "user", "content": "test"}])

    def test_count_tokens_heuristic(self):
        provider, _, _ = self._make_provider()
        # Anthropic uses char-based heuristic from BaseLLMProvider
        text = "a" * 400
        count = provider.count_tokens(text)
        assert count == 100


# ---------------------------------------------------------------------------
# Ollama Provider tests
# ---------------------------------------------------------------------------

class TestOllamaProvider:
    """Tests for OllamaProvider using mocked requests."""

    def _make_provider(self, config=None):
        if config is None:
            config = make_config(provider="ollama", ollama_host="http://localhost:11434")
        from src.summarizer.llm.providers.ollama_provider import OllamaProvider
        p = OllamaProvider(config)
        return p

    def test_get_default_model(self):
        provider = self._make_provider()
        assert provider.get_default_model() == "llama3.2"

    def test_get_default_model_from_config(self):
        config = make_config(provider="ollama", model="mistral")
        provider = self._make_provider(config)
        assert provider.get_default_model() == "mistral"

    def test_host_trailing_slash_stripped(self):
        config = make_config(provider="ollama", ollama_host="http://localhost:11434/")
        provider = self._make_provider(config)
        assert not provider.host.endswith("/")

    def test_complete_success(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"role": "assistant", "content": "Ollama summary"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = provider.complete([{"role": "user", "content": "summarize"}])
            assert result == "Ollama summary"
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert call_kwargs[1]["json"]["model"] == "llama3.2"
            assert call_kwargs[1]["json"]["stream"] is False

    def test_complete_uses_kwargs_model(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "ok"}}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            provider.complete([{"role": "user", "content": "hi"}], model="mistral")
            payload = mock_post.call_args[1]["json"]
            assert payload["model"] == "mistral"

    def test_complete_passes_max_tokens(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "ok"}}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            provider.complete([{"role": "user", "content": "hi"}], max_tokens=256)
            payload = mock_post.call_args[1]["json"]
            assert payload["options"]["num_predict"] == 256

    def test_complete_connection_error(self):
        import requests as req
        provider = self._make_provider()
        with patch("requests.post", side_effect=req.ConnectionError("refused")):
            with pytest.raises(LLMError, match="Cannot connect to Ollama"):
                provider.complete([{"role": "user", "content": "test"}])

    def test_complete_timeout_error(self):
        import requests as req
        provider = self._make_provider()
        with patch("requests.post", side_effect=req.Timeout("timed out")):
            with pytest.raises(LLMError, match="timed out"):
                provider.complete([{"role": "user", "content": "test"}])

    def test_complete_http_error(self):
        import requests as req
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "model not found"}
        http_err = req.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_err

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(LLMError, match="model not found"):
                provider.complete([{"role": "user", "content": "test"}])

    def test_list_models_success(self):
        provider = self._make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
                {"name": "codellama"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            models = provider.list_models()
            assert models == ["llama3.2", "mistral", "codellama"]

    def test_list_models_connection_error(self):
        import requests as req
        provider = self._make_provider()
        with patch("requests.get", side_effect=req.ConnectionError("refused")):
            with pytest.raises(LLMError, match="Cannot connect to Ollama"):
                provider.list_models()

    def test_count_tokens_heuristic(self):
        provider = self._make_provider()
        count = provider.count_tokens("a" * 800)
        assert count == 200


# ---------------------------------------------------------------------------
# Model default verification
# ---------------------------------------------------------------------------

class TestProviderModelDefaults:
    """Verify each provider reports a sensible default model."""

    def test_openai_default_model(self):
        from src.summarizer.llm.providers.openai_provider import DEFAULT_MODEL
        assert DEFAULT_MODEL  # non-empty string
        assert "gpt" in DEFAULT_MODEL

    def test_anthropic_default_model(self):
        from src.summarizer.llm.providers.anthropic_provider import DEFAULT_MODEL
        assert DEFAULT_MODEL
        assert "claude" in DEFAULT_MODEL

    def test_ollama_default_model(self):
        from src.summarizer.llm.providers.ollama_provider import DEFAULT_MODEL
        assert DEFAULT_MODEL
        # Ollama default should be a known open model
        assert len(DEFAULT_MODEL) > 2