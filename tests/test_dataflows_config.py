"""Tests for tradingagents/dataflows/config.py"""

import pytest
from unittest.mock import patch, MagicMock
import importlib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_config_module():
    """Reset the config module's internal _config state to None so each test
    starts from a clean slate."""
    import tradingagents.dataflows.config as cfg_mod
    cfg_mod._config = None


# ---------------------------------------------------------------------------
# initialize_config
# ---------------------------------------------------------------------------

def test_initialize_config_sets_config_from_defaults():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod
    cfg_mod.initialize_config()
    assert cfg_mod._config is not None


def test_initialize_config_copies_default_config():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod
    import tradingagents.default_config as dc

    cfg_mod.initialize_config()
    # Should be a copy, not the same object
    assert cfg_mod._config is not dc.DEFAULT_CONFIG
    # But values should match
    for key, value in dc.DEFAULT_CONFIG.items():
        assert cfg_mod._config[key] == value


def test_initialize_config_does_not_reinitialize_if_already_set():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg_mod.initialize_config()
    cfg_mod._config["__sentinel__"] = "alive"
    cfg_mod.initialize_config()  # second call should be a no-op
    assert cfg_mod._config.get("__sentinel__") == "alive"


# ---------------------------------------------------------------------------
# set_config
# ---------------------------------------------------------------------------

def test_set_config_updates_existing_key():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg_mod.initialize_config()
    cfg_mod.set_config({"llm_provider": "anthropic"})
    assert cfg_mod._config["llm_provider"] == "anthropic"


def test_set_config_adds_new_key():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg_mod.initialize_config()
    cfg_mod.set_config({"custom_key": "custom_value"})
    assert cfg_mod._config["custom_key"] == "custom_value"


def test_set_config_initializes_if_config_is_none():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    assert cfg_mod._config is None
    cfg_mod.set_config({"llm_provider": "google"})
    # Should have initialized from defaults and then applied update
    assert cfg_mod._config is not None
    assert cfg_mod._config["llm_provider"] == "google"


def test_set_config_preserves_unrelated_keys():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg_mod.initialize_config()
    original_max_rounds = cfg_mod._config["max_debate_rounds"]
    cfg_mod.set_config({"llm_provider": "anthropic"})
    assert cfg_mod._config["max_debate_rounds"] == original_max_rounds


def test_set_config_multiple_keys_at_once():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg_mod.initialize_config()
    cfg_mod.set_config({"llm_provider": "google", "max_debate_rounds": 5})
    assert cfg_mod._config["llm_provider"] == "google"
    assert cfg_mod._config["max_debate_rounds"] == 5


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------

def test_get_config_returns_dict():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    result = cfg_mod.get_config()
    assert isinstance(result, dict)


def test_get_config_returns_copy_not_reference():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    result = cfg_mod.get_config()
    result["mutated"] = True
    # Internal state should be unaffected
    assert "mutated" not in cfg_mod._config


def test_get_config_auto_initializes_when_none():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    assert cfg_mod._config is None
    result = cfg_mod.get_config()
    assert result is not None
    assert cfg_mod._config is not None


def test_get_config_reflects_set_config_changes():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg_mod.initialize_config()
    cfg_mod.set_config({"output_language": "Chinese"})
    result = cfg_mod.get_config()
    assert result["output_language"] == "Chinese"


# ---------------------------------------------------------------------------
# Default value checks
# ---------------------------------------------------------------------------

def test_default_llm_provider_is_openai():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg = cfg_mod.get_config()
    assert cfg["llm_provider"] == "openai"


def test_default_data_vendors_present():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg = cfg_mod.get_config()
    assert "data_vendors" in cfg
    vendors = cfg["data_vendors"]
    assert "core_stock_apis" in vendors
    assert "technical_indicators" in vendors
    assert "fundamental_data" in vendors
    assert "news_data" in vendors


def test_default_data_vendor_is_yfinance():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg = cfg_mod.get_config()
    for category, vendor in cfg["data_vendors"].items():
        assert vendor == "yfinance", f"Expected yfinance for {category}, got {vendor}"


def test_default_tool_vendors_is_empty():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg = cfg_mod.get_config()
    assert "tool_vendors" in cfg
    assert cfg["tool_vendors"] == {}


def test_default_max_debate_rounds():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg = cfg_mod.get_config()
    assert cfg["max_debate_rounds"] == 1


def test_default_output_language_is_english():
    _reset_config_module()
    import tradingagents.dataflows.config as cfg_mod

    cfg = cfg_mod.get_config()
    assert cfg["output_language"] == "English"
