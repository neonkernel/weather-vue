"""Tests for all LLM provider implementations."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.summarizer.exceptions import LLMError
from src.summarizer.llm.base import BaseLLMProvider
from src.summarizer.llm.factory import ProviderFactory
from src.summarizer.llm.providers.anthropic_provider import AnthropicProvider
from src.summarizer.llm.providers.ollama_provider import OllamaProvider
from src.summarizer.llm.providers.openai_provider import OpenAIProvider


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Say hello."},
]


# ---------------------------------------------------------------------------
# BaseLLMProvider — interface contract
# ---------------------------------------------------------------------------


def test_base_provider_is_abstract() -> None:
    """Instantiating BaseLLMProvider directly should raise TypeError."""
    with pytest.raises(TypeError):
        BaseLLMProvider()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_openai_module():
    """Patch the openai module so no real network calls happen."""
    with patch.dict("sys.modules", {"openai": MagicMock(), "tiktoken": MagicMock()}):
        import importlib
        import sys

        # Provide minimal openai exception classes
        openai_mock = sys.modules["openai"]
        openai_mock.AuthenticationError = type("AuthenticationError", (Exception,), {})
        openai_mock.RateLimitError = type("RateLimitError", (Exception,), {})
        openai_mock.BadRequestError = type("BadRequestError", (Exception,), {})
        openai_mock.APIConnectionError = type("APIConnectionError", (Exception,), {})
        openai_mock.APIError = type("APIError", (Exception,), {})

        # tiktoken mock
        tiktoken_mock = sys.modules["tiktoken"]
        enc_mock = MagicMock()
        enc_mock.encode.return_value = list(range(5))
        tiktoken_mock.encoding_for_model.return_value = enc_mock
        tiktoken_mock.get_encoding.return_value = enc_mock

        yield openai_mock


def _make_openai_response(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


def test_openai_provider_complete(mock_openai_module) -> None:
    client_mock = MagicMock()
    mock_openai_module.OpenAI.return_value = client_mock
    client_mock.chat.completions.create.return_value = _make_openai_response(
        "Hello!"
    )

    provider = OpenAIProvider(api_key="sk-test")
    result = provider.complete(SAMPLE_MESSAGES)

    assert result == "Hello!"
    client_mock.chat.completions.create.assert_called_once()


def test_openai_provider_default_model(mock_openai_module) -> None:
    mock_openai_module.OpenAI.return_value = MagicMock()
    provider = OpenAIProvider(api_key="sk-test")
    assert provider.default_model == "gpt-4o"
    assert provider.provider_name == "openai"


def test_openai_provider_count_tokens(mock_openai_module) -> None:
    mock_openai_module.OpenAI.return_value = MagicMock()
    provider = OpenAIProvider(api_key="sk-test")
    # tiktoken mock returns list(range(5)) → 5 tokens
    assert provider.count_tokens("some text here") == 5


def test_openai_provider_auth_error(mock_openai_module) -> None:
    client_mock = MagicMock()
    mock_openai_module.OpenAI.return_value = client_mock
    client_mock.chat.completions.create.side_effect = (
        mock_openai_module.AuthenticationError("bad key")
    )

    provider = OpenAIProvider(api_key="bad-key")
    with pytest.raises(LLMError, match="authentication"):
        provider.complete(SAMPLE_MESSAGES)


def test_openai_provider_rate_limit_error(mock_openai_module) -> None:
    client_mock = MagicMock()
    mock_openai_module.OpenAI.return_value = client_mock
    client_mock.chat.completions.create.side_effect = (
        mock_openai_module.RateLimitError("rate limited")
    )

    provider = OpenAIProvider(api_key="sk-test")
    with pytest.raises(LLMError, match="rate limit"):
        provider.complete(SAMPLE_MESSAGES)


def test_openai_provider_empty_response(mock_openai_module) -> None:
    client_mock = MagicMock()
    mock_openai_module.OpenAI.return_value = client_mock
    client_mock.chat.completions.create.return_value = _make_openai_response(None)

    provider = OpenAIProvider(api_key="sk-test")
    with pytest.raises(LLMError, match="empty"):
        provider.complete(SAMPLE_MESSAGES)


def test_openai_provider_kwargs_override(mock_openai_module) -> None:
    client_mock = MagicMock()
    mock_openai_module.OpenAI.return_value = client_mock
    client_mock.chat.completions.create.return_value = _make_openai_response("OK")

    provider = OpenAIProvider(api_key="sk-test", model="gpt-4o", temperature=0.5)
    provider.complete(SAMPLE_MESSAGES, temperature=0.0, max_tokens=100)

    call_kwargs = client_mock.chat.completions.create.call_args[1]
    assert call_kwargs["temperature"] == 0.0
    assert call_kwargs["max_tokens"] == 100


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_anthropic_module():
    """Patch the anthropic module."""
    with patch.dict("sys.modules", {"anthropic": MagicMock()}):
        import sys

        anthropic_mock = sys.modules["anthropic"]
        anthropic_mock.AuthenticationError = type(
            "AuthenticationError", (Exception,), {}
        )
        anthropic_mock.RateLimitError = type("RateLimitError", (Exception,), {})
        anthropic_mock.BadRequestError = type("BadRequestError", (Exception,), {})
        anthropic_mock.APIConnectionError = type(
            "APIConnectionError", (Exception,), {}
        )
        anthropic_mock.APIError = type("APIError", (Exception,), {})

        yield anthropic_mock


def _make_anthropic_response(text: str) -> MagicMock:
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def test_anthropic_provider_complete(mock_anthropic_module) -> None:
    client_mock = MagicMock()
    mock_anthropic_module.Anthropic.return_value = client_mock
    client_mock.messages.create.return_value = _make_anthropic_response(
        "Hello from Claude!"
    )

    provider = AnthropicProvider(api_key="ant-test")
    result = provider.complete(SAMPLE_MESSAGES)

    assert result == "Hello from Claude!"


def test_anthropic_provider_default_model(mock_anthropic_module) -> None:
    mock_anthropic_module.Anthropic.return_value = MagicMock()
    provider = AnthropicProvider(api_key="ant-test")
    assert "claude" in provider.default_model
    assert provider.provider_name == "anthropic"


def test_anthropic_provider_separates_system_message(mock_anthropic_module) -> None:
    client_mock = MagicMock()
    mock_anthropic_module.Anthropic.return_value = client_mock
    client_mock.messages.create.return_value = _make_anthropic_response("ok")

    provider = AnthropicProvider(api_key="ant-test")
    provider.complete(SAMPLE_MESSAGES)

    call_kwargs = client_mock.messages.create.call_args[1]
    # System message should be pulled out into the 'system' kwarg
    assert "system" in call_kwargs
    assert call_kwargs["system"] == "You are a helpful assistant."
    # Only the user turn should be in 'messages'
    assert call_kwargs["messages"] == [{"role": "user", "content": "Say hello."}]


def test_anthropic_provider_no_system_message(mock_anthropic_module) -> None:
    client_mock = MagicMock()
    mock_anthropic_module.Anthropic.return_value = client_mock
    client_mock.messages.create.return_value = _make_anthropic_response("ok")

    provider = AnthropicProvider(api_key="ant-test")
    messages = [{"role": "user", "content": "Hello"}]
    provider.complete(messages)

    call_kwargs = client_mock.messages.create.call_args[1]
    assert "system" not in call_kwargs


def test_anthropic_provider_count_tokens(mock_anthropic_module) -> None:
    mock_anthropic_module.Anthropic.return_value = MagicMock()
    provider = AnthropicProvider(api_key="ant-test")
    text = "Hello world"  # 11 chars → max(1, 11//4) = 2
    assert provider.count_tokens(text) == 2


def test_anthropic_provider_auth_error(mock_anthropic_module) -> None:
    client_mock = MagicMock()
    mock_anthropic_module.Anthropic.return_value = client_mock
    client_mock.messages.create.side_effect = (
        mock_anthropic_module.AuthenticationError("bad key")
    )

    provider = AnthropicProvider(api_key="bad-key")
    with pytest.raises(LLMError, match="authentication"):
        provider.complete(SAMPLE_MESSAGES)


def test_anthropic_provider_rate_limit_error(mock_anthropic_module) -> None:
    client_mock = MagicMock()
    mock_anthropic_module.Anthropic.return_value = client_mock
    client_mock.messages.create.side_effect = (
        mock_anthropic_module.RateLimitError("rate limited")
    )

    provider = AnthropicProvider(api_key="ant-test")
    with pytest.raises(LLMError, match="rate limit"):
        provider.complete(SAMPLE_MESSAGES)


def test_anthropic_provider_empty_response(mock_anthropic_module) -> None:
    client_mock = MagicMock()
    mock_anthropic_module.Anthropic.return_value = client_mock
    resp = MagicMock()
    resp.content = []
    client_mock.messages.create.return_value = resp

    provider = AnthropicProvider(api_key="ant-test")
    with pytest.raises(LLMError, match="empty"):
        provider.complete(SAMPLE_MESSAGES)


def test_anthropic_no_user_messages_raises(mock_anthropic_module) -> None:
    mock_anthropic_module.Anthropic.return_value = MagicMock()
    provider = AnthropicProvider(api_key="ant-test")
    with pytest.raises(LLMError, match="non-system"):
        provider.complete([{"role": "system", "content": "Only system"}])


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_requests():
    """Patch the requests module for Ollama tests."""
    with patch("src.summarizer.llm.providers.ollama_provider.requests") as req_mock:
        # Provide exception classes
        req_mock.exceptions = MagicMock()
        req_mock.exceptions.ConnectionError = ConnectionError
        req_mock.exceptions.Timeout = TimeoutError
        req_mock.exceptions.RequestException = Exception
        yield req_mock


def _make_requests_response(
    status_code: int = 200, json_data: dict | None = None, text: str = ""
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.text = text or json.dumps(json_data or {})
    resp.json.return_value = json_data or {}
    return resp


def test_ollama_provider_complete(mock_requests) -> None:
    mock_requests.post.return_value = _make_requests_response(
        200,
        {"message": {"role": "assistant", "content": "Hi from Ollama!"}},
    )

    provider = OllamaProvider()
    result = provider.complete(SAMPLE_MESSAGES)
    assert result == "Hi from Ollama!"


def test_ollama_provider_default_model() -> None:
    provider = OllamaProvider.__new__(OllamaProvider)
    provider._host = "http://localhost:11434"
    provider._model = "llama3"
    provider._temperature = 0.3
    provider._max_tokens = 4096
    assert provider.default_model == "llama3"
    assert provider.provider_name == "ollama"


def test_ollama_provider_count_tokens() -> None:
    provider = OllamaProvider.__new__(OllamaProvider)
    text = "Hello world!"  # 12 chars → max(1, 12//4) = 3
    assert provider.count_tokens(text) == 3


def test_ollama_provider_connection_error(mock_requests) -> None:
    mock_requests.post.side_effect = ConnectionError("refused")

    provider = OllamaProvider()
    with pytest.raises(LLMError, match="connect"):
        provider.complete(SAMPLE_MESSAGES)


def test_ollama_provider_model_not_found(mock_requests) -> None:
    mock_requests.post.return_value = _make_requests_response(
        404, text="model not found"
    )

    provider = OllamaProvider(model="nonexistent")
    with pytest.raises(LLMError, match="not found"):
        provider.complete(SAMPLE_MESSAGES)


def test_ollama_provider_http_error(mock_requests) -> None:
    mock_requests.post.return_value = _make_requests_response(
        500, text="internal server error"
    )

    provider = OllamaProvider()
    with pytest.raises(LLMError, match="HTTP 500"):
        provider.complete(SAMPLE_MESSAGES)


def test_ollama_provider_bad_json(mock_requests) -> None:
    resp = MagicMock()
    resp.status_code = 200
    resp.ok = True
    resp.text = "not valid json"
    resp.json.side_effect = json.JSONDecodeError("err", "doc", 0)
    mock_requests.post.return_value = resp

    provider = OllamaProvider()
    with pytest.raises(LLMError, match="JSON"):
        provider.complete(SAMPLE_MESSAGES)


def test_ollama_provider_unexpected_structure(mock_requests) -> None:
    mock_requests.post.return_value = _make_requests_response(
        200, {"unexpected": "structure"}
    )

    provider = OllamaProvider()
    with pytest.raises(LLMError, match="structure"):
        provider.complete(SAMPLE_MESSAGES)


def test_ollama_provider_custom_host(mock_requests) -> None:
    mock_requests.post.return_value = _make_requests_response(
        200, {"message": {"role": "assistant", "content": "ok"}}
    )

    provider = OllamaProvider(host="http://192.168.1.100:11434")
    provider.complete(SAMPLE_MESSAGES)

    call_args = mock_requests.post.call_args
    assert "192.168.1.100" in call_args[0][0]


def test_ollama_provider_list_models(mock_requests) -> None:
    mock_requests.get.return_value = _make_requests_response(
        200,
        {"models": [{"name": "llama3"}, {"name": "mistral"}]},
    )

    provider = OllamaProvider()
    models = provider.list_models()
    assert models == ["llama3", "mistral"]


def test_ollama_provider_list_models_error(mock_requests) -> None:
    mock_requests.get.side_effect = ConnectionError("refused")

    provider = OllamaProvider()
    with pytest.raises(LLMError, match="list Ollama models"):
        provider.list_models()


# ---------------------------------------------------------------------------
# ProviderFactory
# ---------------------------------------------------------------------------


def test_factory_unknown_provider() -> None:
    with pytest.raises(LLMError, match="Unknown provider"):
        ProviderFactory.create(provider_name="grok")


def test_factory_openai_missing_key() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(LLMError, match="API key"):
            ProviderFactory.create(provider_name="openai")


def test_factory_anthropic_missing_key() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(LLMError, match="API key"):
            ProviderFactory.create(provider_name="anthropic")


def test_factory_reads_env_provider(mock_requests) -> None:
    """Factory should fall back to LLM_PROVIDER env var."""
    mock_requests.post.return_value = _make_requests_response(
        200, {"message": {"role": "assistant", "content": "ok"}}
    )
    with patch.dict("os.environ", {"LLM_PROVIDER": "ollama"}, clear=False):
        provider = ProviderFactory.create()
    assert provider.provider_name == "ollama"


def test_factory_explicit_name_overrides_env(mock_requests) -> None:
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai"}, clear=False):
        provider = ProviderFactory.create(provider_name="ollama")
    assert provider.provider_name == "ollama"


def test_factory_creates_ollama_with_custom_host(mock_requests) -> None:
    from src.summarizer.config import SummarizerConfig

    config = SummarizerConfig(
        provider="ollama",
        ollama_host="http://remote-host:11434",
    )
    provider = ProviderFactory.create(config=config)
    assert isinstance(provider, OllamaProvider)
    assert provider._host == "http://remote-host:11434"