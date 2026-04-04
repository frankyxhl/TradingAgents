"""Tests for tradingagents/llm_clients/factory.py"""

import pytest

from tradingagents.llm_clients.anthropic_client import AnthropicClient
from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.llm_clients.google_client import GoogleClient
from tradingagents.llm_clients.openai_client import OpenAIClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_openai(model="gpt-4o", provider="openai", base_url=None, **kw):
    return create_llm_client(provider, model, base_url, **kw)


# ---------------------------------------------------------------------------
# Provider → client class routing
# ---------------------------------------------------------------------------


def test_openai_provider_returns_openai_client():
    client = _make_openai(provider="openai")
    assert isinstance(client, OpenAIClient)


def test_openai_provider_case_insensitive():
    client = _make_openai(provider="OpenAI")
    assert isinstance(client, OpenAIClient)


def test_zai_provider_returns_openai_client():
    client = _make_openai(provider="zai")
    assert isinstance(client, OpenAIClient)


def test_xai_provider_returns_openai_client():
    client = _make_openai(provider="xai")
    assert isinstance(client, OpenAIClient)


def test_ollama_provider_returns_openai_client():
    client = _make_openai(provider="ollama")
    assert isinstance(client, OpenAIClient)


def test_openrouter_provider_returns_openai_client():
    client = _make_openai(provider="openrouter")
    assert isinstance(client, OpenAIClient)


def test_anthropic_provider_returns_anthropic_client():
    client = create_llm_client("anthropic", "claude-3-5-sonnet-20241022")
    assert isinstance(client, AnthropicClient)


def test_anthropic_provider_case_insensitive():
    client = create_llm_client("Anthropic", "claude-3-5-sonnet-20241022")
    assert isinstance(client, AnthropicClient)


def test_google_provider_returns_google_client():
    client = create_llm_client("google", "gemini-2.0-flash")
    assert isinstance(client, GoogleClient)


def test_google_provider_case_insensitive():
    client = create_llm_client("Google", "gemini-2.0-flash")
    assert isinstance(client, GoogleClient)


# ---------------------------------------------------------------------------
# Unknown provider raises ValueError
# ---------------------------------------------------------------------------


def test_unknown_provider_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_client("bogus_provider", "some-model")


def test_unknown_provider_message_includes_name():
    with pytest.raises(ValueError, match="bogus_provider"):
        create_llm_client("bogus_provider", "some-model")


# ---------------------------------------------------------------------------
# Model and base_url are forwarded to the client
# ---------------------------------------------------------------------------


def test_model_is_stored_on_client():
    client = create_llm_client("openai", "gpt-4o-mini")
    assert client.model == "gpt-4o-mini"


def test_base_url_is_stored_on_client():
    client = create_llm_client("openai", "gpt-4o", base_url="https://custom.endpoint/v1")
    assert client.base_url == "https://custom.endpoint/v1"


def test_kwargs_are_stored_on_client():
    client = create_llm_client("openai", "gpt-4o", timeout=30)
    assert client.kwargs.get("timeout") == 30


# ---------------------------------------------------------------------------
# Provider string is lowercased and forwarded to OpenAIClient
# ---------------------------------------------------------------------------


def test_zai_provider_string_stored_on_openai_client():
    client = create_llm_client("zai", "glm-4-plus")
    assert isinstance(client, OpenAIClient)
    assert client.provider == "zai"


def test_ollama_provider_string_stored_on_openai_client():
    client = create_llm_client("ollama", "llama3")
    assert client.provider == "ollama"
