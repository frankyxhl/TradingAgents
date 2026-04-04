"""Tests for tradingagents/llm_clients/anthropic_client.py"""

import pytest
from unittest.mock import patch, MagicMock

from tradingagents.llm_clients.anthropic_client import (
    AnthropicClient,
    NormalizedChatAnthropic,
    _PASSTHROUGH_KWARGS,
)


# ---------------------------------------------------------------------------
# AnthropicClient construction
# ---------------------------------------------------------------------------

def test_client_stores_model():
    client = AnthropicClient("claude-3-5-sonnet-20241022")
    assert client.model == "claude-3-5-sonnet-20241022"


def test_client_stores_base_url():
    client = AnthropicClient("claude-3-5-sonnet-20241022", base_url="https://proxy.example.com")
    assert client.base_url == "https://proxy.example.com"


def test_client_base_url_defaults_to_none():
    client = AnthropicClient("claude-3-5-sonnet-20241022")
    assert client.base_url is None


def test_client_stores_extra_kwargs():
    client = AnthropicClient("claude-3-5-sonnet-20241022", timeout=30)
    assert client.kwargs["timeout"] == 30


# ---------------------------------------------------------------------------
# get_llm — basic construction
# ---------------------------------------------------------------------------

def test_get_llm_returns_normalized_chat_anthropic_instance():
    client = AnthropicClient("claude-3-5-sonnet-20241022")
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        result = client.get_llm()
        assert result is MockChat.return_value


def test_get_llm_passes_model_to_constructor():
    client = AnthropicClient("claude-3-5-sonnet-20241022")
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["model"] == "claude-3-5-sonnet-20241022"


# ---------------------------------------------------------------------------
# get_llm — base_url handling
# ---------------------------------------------------------------------------

def test_get_llm_forwards_base_url_when_provided():
    client = AnthropicClient("claude-3-5-sonnet-20241022", base_url="https://proxy.example.com")
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["base_url"] == "https://proxy.example.com"


def test_get_llm_omits_base_url_when_none():
    client = AnthropicClient("claude-3-5-sonnet-20241022")
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert "base_url" not in MockChat.call_args.kwargs


# ---------------------------------------------------------------------------
# get_llm — API key passthrough
# ---------------------------------------------------------------------------

def test_get_llm_forwards_api_key_kwarg():
    client = AnthropicClient("claude-3-5-sonnet-20241022", api_key="sk-ant-test-key")
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["api_key"] == "sk-ant-test-key"


def test_get_llm_omits_api_key_when_not_provided():
    client = AnthropicClient("claude-3-5-sonnet-20241022")
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert "api_key" not in MockChat.call_args.kwargs


# ---------------------------------------------------------------------------
# get_llm — additional passthrough kwargs
# ---------------------------------------------------------------------------

def test_get_llm_forwards_timeout():
    client = AnthropicClient("claude-3-5-sonnet-20241022", timeout=60)
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["timeout"] == 60


def test_get_llm_forwards_max_retries():
    client = AnthropicClient("claude-3-5-sonnet-20241022", max_retries=3)
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["max_retries"] == 3


def test_get_llm_forwards_max_tokens():
    client = AnthropicClient("claude-3-5-sonnet-20241022", max_tokens=1024)
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert MockChat.call_args.kwargs["max_tokens"] == 1024


def test_get_llm_does_not_forward_unknown_kwargs():
    client = AnthropicClient("claude-3-5-sonnet-20241022", something_unknown="nope")
    with patch(
        "tradingagents.llm_clients.anthropic_client.NormalizedChatAnthropic",
        return_value=MagicMock(),
    ) as MockChat:
        client.get_llm()
        assert "something_unknown" not in MockChat.call_args.kwargs


# ---------------------------------------------------------------------------
# passthrough kwargs list coverage
# ---------------------------------------------------------------------------

def test_passthrough_kwargs_includes_required_keys():
    for key in ("timeout", "max_retries", "api_key", "max_tokens"):
        assert key in _PASSTHROUGH_KWARGS


# ---------------------------------------------------------------------------
# validate_model delegates to validator
# ---------------------------------------------------------------------------

def test_validate_model_delegates_to_validator():
    client = AnthropicClient("claude-3-5-sonnet-20241022")
    with patch(
        "tradingagents.llm_clients.anthropic_client.validate_model", return_value=True
    ) as mock_v:
        result = client.validate_model()
        mock_v.assert_called_once_with("anthropic", "claude-3-5-sonnet-20241022")
        assert result is True


def test_validate_model_returns_false_for_unknown_model():
    client = AnthropicClient("not-a-real-claude-model")
    with patch(
        "tradingagents.llm_clients.anthropic_client.validate_model", return_value=False
    ) as mock_v:
        result = client.validate_model()
        assert result is False
