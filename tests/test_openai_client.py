"""Tests for tradingagents/llm_clients/openai_client.py"""

from unittest.mock import MagicMock, patch

from tradingagents.llm_clients.openai_client import (
    _PROVIDER_CONFIG,
    OpenAIClient,
)

# ---------------------------------------------------------------------------
# _PROVIDER_CONFIG shape
# ---------------------------------------------------------------------------


def test_zai_base_url_is_z_ai_coding_endpoint():
    base_url, _ = _PROVIDER_CONFIG["zai"]
    assert base_url == "https://api.z.ai/api/coding/paas/v4"


def test_zai_api_key_env_var():
    _, api_key_env = _PROVIDER_CONFIG["zai"]
    assert api_key_env == "ZAI_API_KEY"


def test_xai_base_url():
    base_url, _ = _PROVIDER_CONFIG["xai"]
    assert base_url == "https://api.x.ai/v1"


def test_xai_api_key_env_var():
    _, api_key_env = _PROVIDER_CONFIG["xai"]
    assert api_key_env == "XAI_API_KEY"


def test_openrouter_base_url():
    base_url, _ = _PROVIDER_CONFIG["openrouter"]
    assert base_url == "https://openrouter.ai/api/v1"


def test_ollama_base_url():
    base_url, _ = _PROVIDER_CONFIG["ollama"]
    assert base_url == "http://localhost:11434/v1"


def test_ollama_api_key_env_is_none():
    _, api_key_env = _PROVIDER_CONFIG["ollama"]
    assert api_key_env is None


# ---------------------------------------------------------------------------
# OpenAIClient construction
# ---------------------------------------------------------------------------


def test_client_stores_model():
    client = OpenAIClient("gpt-4o")
    assert client.model == "gpt-4o"


def test_client_stores_base_url():
    client = OpenAIClient("gpt-4o", base_url="https://custom/v1")
    assert client.base_url == "https://custom/v1"


def test_client_default_provider_is_openai():
    client = OpenAIClient("gpt-4o")
    assert client.provider == "openai"


def test_client_stores_provider_lowercased():
    client = OpenAIClient("gpt-4o", provider="ZAI")
    assert client.provider == "zai"


def test_client_stores_extra_kwargs():
    client = OpenAIClient("gpt-4o", timeout=60)
    assert client.kwargs["timeout"] == 60


# ---------------------------------------------------------------------------
# get_llm — OpenAI (native, uses Responses API)
# ---------------------------------------------------------------------------


def test_get_llm_openai_uses_responses_api():
    client = OpenAIClient("gpt-4o", provider="openai")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        call_kwargs = MockChat.call_args.kwargs
        assert call_kwargs.get("use_responses_api") is True


def test_get_llm_openai_passes_model():
    client = OpenAIClient("gpt-4o-mini", provider="openai")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["model"] == "gpt-4o-mini"


def test_get_llm_openai_no_hardcoded_base_url():
    """Native OpenAI does not inject a base_url unless the user supplies one."""
    client = OpenAIClient("gpt-4o", provider="openai")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        call_kwargs = MockChat.call_args.kwargs
        assert "base_url" not in call_kwargs


# ---------------------------------------------------------------------------
# get_llm — ZAI provider
# ---------------------------------------------------------------------------


def test_get_llm_zai_uses_z_ai_base_url():
    client = OpenAIClient("glm-4-plus", provider="zai")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        call_kwargs = MockChat.call_args.kwargs
        assert call_kwargs["base_url"] == "https://api.z.ai/api/coding/paas/v4"


def test_get_llm_zai_reads_api_key_from_env(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key-123")
    client = OpenAIClient("glm-4-plus", provider="zai")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        call_kwargs = MockChat.call_args.kwargs
        assert call_kwargs["api_key"] == "test-zai-key-123"


def test_get_llm_zai_no_api_key_in_kwargs_when_env_unset(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    client = OpenAIClient("glm-4-plus", provider="zai")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        call_kwargs = MockChat.call_args.kwargs
        # api_key should not be set when env var is absent
        assert "api_key" not in call_kwargs


def test_get_llm_zai_does_not_set_responses_api():
    """ZAI is a third-party provider; Responses API flag should NOT be set."""
    client = OpenAIClient("glm-4-plus", provider="zai")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        call_kwargs = MockChat.call_args.kwargs
        assert call_kwargs.get("use_responses_api") is not True


# ---------------------------------------------------------------------------
# get_llm — Ollama (api_key set to "ollama")
# ---------------------------------------------------------------------------


def test_get_llm_ollama_sets_api_key_to_literal_ollama():
    client = OpenAIClient("llama3", provider="ollama")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["api_key"] == "ollama"


def test_get_llm_ollama_uses_localhost_base_url():
    client = OpenAIClient("llama3", provider="ollama")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["base_url"] == "http://localhost:11434/v1"


# ---------------------------------------------------------------------------
# get_llm — custom base_url for unknown providers (e.g. plain "openai" + override)
# ---------------------------------------------------------------------------


def test_get_llm_custom_base_url_for_openai_provider():
    """When provider is openai but user supplies a custom base_url, it is forwarded."""
    client = OpenAIClient("gpt-4o", base_url="https://proxy.example.com/v1", provider="openai")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        # openai provider doesn't have a _PROVIDER_CONFIG entry, so base_url branch applies
        call_kwargs = MockChat.call_args.kwargs
        assert call_kwargs.get("base_url") == "https://proxy.example.com/v1"


# ---------------------------------------------------------------------------
# Passthrough kwargs forwarding
# ---------------------------------------------------------------------------


def test_get_llm_forwards_timeout_kwarg():
    client = OpenAIClient("gpt-4o", provider="openai", timeout=45)
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["timeout"] == 45


def test_get_llm_forwards_max_retries_kwarg():
    client = OpenAIClient("gpt-4o", provider="openai", max_retries=2)
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["max_retries"] == 2


def test_get_llm_does_not_forward_unknown_kwargs():
    client = OpenAIClient("gpt-4o", provider="openai", something_random="value")
    with patch(
        "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert "something_random" not in MockChat.call_args.kwargs


# ---------------------------------------------------------------------------
# validate_model delegates correctly
# ---------------------------------------------------------------------------


def test_validate_model_delegates_to_validator():
    client = OpenAIClient("gpt-4o", provider="openai")
    with patch(
        "tradingagents.llm_clients.openai_client.validate_model", return_value=True
    ) as mock_v:
        result = client.validate_model()
        mock_v.assert_called_once_with("openai", "gpt-4o")
        assert result is True
