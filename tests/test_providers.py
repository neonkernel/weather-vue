"""Tests for LLM provider implementations."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, Mock, patch, PropertyMock
import pytest

from summarizer.config import SummarizerConfig
from summarizer.exceptions import LLMError


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_config(**kwargs) -> SummarizerConfig:
    """Create a SummarizerConfig with test-safe defaults."""
    defaults = {
        "openai_api_key": "sk-test-openai",
        "anthropic_api_key": "sk-test-anthropic",
        "ollama_host": "http://localhost:11434",
        "max_tokens": 512,
    }
    defaults.update(kwargs)
    return SummarizerConfig(**defaults)


SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarize: hello world."},
]

# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    def _make_provider(self, **kwargs):
        with patch("openai.OpenAI"):
            from summarizer.llm.providers.openai_provider import OpenAIProvider
            cfg = make_config(provider="openai", **kwargs)
            provider = OpenAIProvider(cfg)
            return provider

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.get_default_model() is not None
        assert len(provider.get_default_model()) > 0

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.get_provider_name() == "openai"

    def test_complete_returns_string(self):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "This is a summary."
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[mock_choice]
            )

            from summarizer.llm.providers.openai_provider import OpenAIProvider
            cfg = make_config(provider="openai")
            provider = OpenAIProvider(cfg)

            result = provider.complete(SAMPLE_MESSAGES)
            assert result == "This is a summary."

    def test_complete_calls_api_with_messages(self):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "Summary here."
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[mock_choice]
            )

            from summarizer.llm.providers.openai_provider import OpenAIProvider
            cfg = make_config(provider="openai")
            provider = OpenAIProvider(cfg)
            provider.complete(SAMPLE_MESSAGES)

            call_kwargs = mock_client.chat.completions.create.call_args
            assert call_kwargs is not None
            assert call_kwargs.kwargs["messages"] == SAMPLE_MESSAGES

    def test_complete_maps_exception_to_llm_error(self):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = RuntimeError("API down")

            from summarizer.llm.providers.openai_provider import OpenAIProvider
            cfg = make_config(provider="openai")
            provider = OpenAIProvider(cfg)

            with pytest.raises(LLMError, match="OpenAI completion failed"):
                provider.complete(SAMPLE_MESSAGES)

    def test_raises_llm_error_without_api_key(self):
        with patch("openai.OpenAI"):
            from summarizer.llm.providers.openai_provider import OpenAIProvider
            cfg = make_config(provider="openai", openai_api_key=None)
            cfg.openai_api_key = None

            with pytest.raises(LLMError, match="API key"):
                OpenAIProvider(cfg)

    def test_count_tokens_returns_positive_int(self):
        provider = self._make_provider()
        count = provider.count_tokens("Hello, world!")
        assert isinstance(count, int)
        assert count > 0

    def test_model_override_in_complete(self):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "ok"
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[mock_choice]
            )

            from summarizer.llm.providers.openai_provider import OpenAIProvider
            cfg = make_config(provider="openai")
            provider = OpenAIProvider(cfg)
            provider.complete(SAMPLE_MESSAGES, model="gpt-4o")

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o"


# ---------------------------------------------------------------------------
# Anthropic Provider
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    def _make_provider(self, **kwargs):
        with patch("anthropic.Anthropic"):
            from summarizer.llm.providers.anthropic_provider import AnthropicProvider
            cfg = make_config(provider="anthropic", **kwargs)
            provider = AnthropicProvider(cfg)
            return provider

    def test_default_model(self):
        provider = self._make_provider()
        assert "claude" in provider.get_default_model().lower()

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.get_provider_name() == "anthropic"

    def test_complete_returns_string(self):
        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_block = MagicMock()
            mock_block.text = "Claude says hi."
            mock_client.messages.create.return_value = MagicMock(
                content=[mock_block]
            )

            from summarizer.llm.providers.anthropic_provider import AnthropicProvider
            cfg = make_config(provider="anthropic")
            provider = AnthropicProvider(cfg)
            result = provider.complete(SAMPLE_MESSAGES)
            assert result == "Claude says hi."

    def test_system_message_is_extracted(self):
        """System role messages should be passed as the 'system' param, not in messages."""
        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_block = MagicMock()
            mock_block.text = "ok"
            mock_client.messages.create.return_value = MagicMock(
                content=[mock_block]
            )

            from summarizer.llm.providers.anthropic_provider import AnthropicProvider
            cfg = make_config(provider="anthropic")
            provider = AnthropicProvider(cfg)
            provider.complete(SAMPLE_MESSAGES)

            call_kwargs = mock_client.messages.create.call_args.kwargs
            # System content should NOT appear in the messages list
            for msg in call_kwargs.get("messages", []):
                assert msg.get("role") != "system"
            # System content should be in the 'system' kwarg
            assert "system" in call_kwargs
            assert "helpful assistant" in call_kwargs["system"]

    def test_complete_maps_exception_to_llm_error(self):
        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create.side_effect = RuntimeError("rate limited")

            from summarizer.llm.providers.anthropic_provider import AnthropicProvider
            cfg = make_config(provider="anthropic")
            provider = AnthropicProvider(cfg)

            with pytest.raises(LLMError, match="Anthropic completion failed"):
                provider.complete(SAMPLE_MESSAGES)

    def test_raises_llm_error_without_api_key(self):
        with patch("anthropic.Anthropic"):
            from summarizer.llm.providers.anthropic_provider import AnthropicProvider
            cfg = make_config(provider="anthropic", anthropic_api_key=None)
            cfg.anthropic_api_key = None

            with pytest.raises(LLMError, match="API key"):
                AnthropicProvider(cfg)

    def test_count_tokens_returns_positive_int(self):
        provider = self._make_provider()
        count = provider.count_tokens("Hello, world! " * 10)
        assert isinstance(count, int)
        assert count > 0

    def test_model_alias_resolution(self):
        """Friendly model alias should be resolved to a canonical model ID."""
        with patch("anthropic.Anthropic"):
            from summarizer.llm.providers.anthropic_provider import AnthropicProvider
            cfg = make_config(provider="anthropic", model="claude-3-5-sonnet")
            provider = AnthropicProvider(cfg)
            # Should be resolved to the dated canonical ID
            assert "20" in provider.get_default_model()

    def test_no_system_kwarg_when_no_system_message(self):
        """When there is no system message, 'system' param should not be passed."""
        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_block = MagicMock()
            mock_block.text = "ok"
            mock_client.messages.create.return_value = MagicMock(
                content=[mock_block]
            )

            from summarizer.llm.providers.anthropic_provider import AnthropicProvider
            cfg = make_config(provider="anthropic")
            provider = AnthropicProvider(cfg)

            user_only = [{"role": "user", "content": "Hello!"}]
            provider.complete(user_only)

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert "system" not in call_kwargs


# ---------------------------------------------------------------------------
# Ollama Provider
# ---------------------------------------------------------------------------

class TestOllamaProvider:
    def _make_provider(self, **kwargs):
        with patch("requests.post"), patch("requests.get"):
            from summarizer.llm.providers.ollama_provider import OllamaProvider
            cfg = make_config(provider="ollama", **kwargs)
            return OllamaProvider(cfg)

    def test_default_model(self):
        provider = self._make_provider()
        assert provider.get_default_model() is not None

    def test_provider_name(self):
        provider = self._make_provider()
        assert provider.get_provider_name() == "ollama"

    def test_complete_returns_string(self):
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama")

        response_body = json.dumps({
            "message": {"role": "assistant", "content": "Ollama says hi."},
            "done": True,
        })

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = response_body
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            provider = OllamaProvider(cfg)
            result = provider.complete(SAMPLE_MESSAGES)
            assert result == "Ollama says hi."

    def test_complete_sends_correct_payload(self):
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama", model="mistral")

        response_body = json.dumps({
            "message": {"role": "assistant", "content": "ok"},
            "done": True,
        })

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = response_body
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            provider = OllamaProvider(cfg)
            provider.complete(SAMPLE_MESSAGES)

            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
            assert payload["messages"] == SAMPLE_MESSAGES
            assert payload["model"] == "mistral"

    def test_connection_error_maps_to_llm_error(self):
        import requests as req_mod
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama")

        with patch("requests.post") as mock_post:
            mock_post.side_effect = req_mod.exceptions.ConnectionError("refused")
            provider = OllamaProvider(cfg)

            with pytest.raises(LLMError, match="Cannot connect to Ollama"):
                provider.complete(SAMPLE_MESSAGES)

    def test_http_error_maps_to_llm_error(self):
        import requests as req_mod
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama")

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            http_err = req_mod.exceptions.HTTPError(response=mock_resp)
            mock_post.side_effect = http_err
            provider = OllamaProvider(cfg)

            with pytest.raises(LLMError, match="HTTP"):
                provider.complete(SAMPLE_MESSAGES)

    def test_timeout_maps_to_llm_error(self):
        import requests as req_mod
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama")

        with patch("requests.post") as mock_post:
            mock_post.side_effect = req_mod.exceptions.Timeout("timed out")
            provider = OllamaProvider(cfg)

            with pytest.raises(LLMError, match="timed out"):
                provider.complete(SAMPLE_MESSAGES)

    def test_list_models(self):
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama")

        tags_response = {
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
                {"name": "codellama"},
            ]
        }

        with patch("requests.post"), patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = tags_response
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            provider = OllamaProvider(cfg)
            models = provider.list_models()

        assert "llama3.2" in models
        assert "mistral" in models
        assert "codellama" in models

    def test_list_models_connection_error(self):
        import requests as req_mod
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama")

        with patch("requests.post"), patch("requests.get") as mock_get:
            mock_get.side_effect = req_mod.exceptions.ConnectionError("refused")
            provider = OllamaProvider(cfg)

            with pytest.raises(LLMError, match="Cannot connect"):
                provider.list_models()

    def test_count_tokens(self):
        provider = self._make_provider()
        count = provider.count_tokens("a" * 400)
        assert count == 100  # 400 chars / 4 = 100

    def test_custom_host_from_config(self):
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama", ollama_host="http://my-server:11434")

        response_body = json.dumps({
            "message": {"role": "assistant", "content": "remote response"},
            "done": True,
        })

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = response_body
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            provider = OllamaProvider(cfg)
            provider.complete(SAMPLE_MESSAGES)

            url_called = mock_post.call_args.args[0]
            assert "my-server:11434" in url_called

    def test_ndjson_streaming_response(self):
        """Provider should handle newline-delimited JSON (streaming) responses."""
        from summarizer.llm.providers.ollama_provider import OllamaProvider
        cfg = make_config(provider="ollama")

        ndjson = "\n".join([
            json.dumps({"message": {"role": "assistant", "content": "Hello"}, "done": False}),
            json.dumps({"message": {"role": "assistant", "content": " World"}, "done": True}),
        ])

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = ndjson
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            provider = OllamaProvider(cfg)
            result = provider.complete(SAMPLE_MESSAGES)
            assert result == "Hello World"


# ---------------------------------------------------------------------------
# ProviderFactory
# ---------------------------------------------------------------------------

class TestProviderFactory:
    def test_creates_openai_provider(self):
        with patch("openai.OpenAI"):
            from summarizer.llm.factory import ProviderFactory
            cfg = make_config(provider="openai")
            provider = ProviderFactory.create(cfg)
            assert provider.get_provider_name() == "openai"

    def test_creates_anthropic_provider(self):
        with patch("anthropic.Anthropic"):
            from summarizer.llm.factory import ProviderFactory
            cfg = make_config(provider="anthropic")
            provider = ProviderFactory.create(cfg)
            assert provider.get_provider_name() == "anthropic"

    def test_creates_ollama_provider(self):
        from summarizer.llm.factory import ProviderFactory
        cfg = make_config(provider="ollama")
        provider = ProviderFactory.create(cfg)
        assert provider.get_provider_name() == "ollama"

    def test_unknown_provider_raises_llm_error(self):
        from summarizer.llm.factory import ProviderFactory
        cfg = make_config(provider="unknown_provider")
        # Override to bypass SummarizerConfig validation
        cfg.provider = "unknown_provider"
        with pytest.raises(LLMError, match="Unknown provider"):
            ProviderFactory.create(cfg)

    def test_list_providers(self):
        from summarizer.llm.factory import ProviderFactory
        providers = ProviderFactory.list_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_env_var_selects_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        from summarizer.llm.factory import ProviderFactory
        # Config with no explicit provider — falls back to env var
        cfg = SummarizerConfig()
        provider = ProviderFactory.create(cfg)
        assert provider.get_provider_name() == "ollama"


# ---------------------------------------------------------------------------
# SummarizerConfig
# ---------------------------------------------------------------------------

class TestSummarizerConfig:
    def test_default_provider_is_openai(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        cfg = SummarizerConfig()
        assert cfg.provider == "openai"

    def test_provider_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        cfg = SummarizerConfig()
        assert cfg.provider == "anthropic"

    def test_validate_raises_for_unknown_provider(self):
        cfg = make_config()
        cfg.provider = "grok"
        with pytest.raises(ValueError, match="Invalid provider"):
            cfg.validate()

    def test_validate_raises_for_openai_without_key(self):
        cfg = make_config(openai_api_key=None)
        cfg.openai_api_key = None
        cfg.provider = "openai"
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            cfg.validate()

    def test_validate_raises_for_anthropic_without_key(self):
        cfg = make_config(anthropic_api_key=None)
        cfg.anthropic_api_key = None
        cfg.provider = "anthropic"
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            cfg.validate()

    def test_validate_passes_for_ollama_without_api_key(self):
        cfg = make_config(openai_api_key=None, anthropic_api_key=None)
        cfg.openai_api_key = None
        cfg.anthropic_api_key = None
        cfg.provider = "ollama"
        # Should not raise
        cfg.validate()

    def test_ollama_host_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        cfg = SummarizerConfig()
        assert cfg.ollama_host == "http://localhost:11434"

    def test_ollama_host_from_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://custom-host:11434")
        cfg = SummarizerConfig()
        assert cfg.ollama_host == "http://custom-host:11434"