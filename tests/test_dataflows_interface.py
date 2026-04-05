"""Tests for tradingagents/dataflows/interface.py"""

from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.alpha_vantage_common import AlphaVantageRateLimitError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_interface():
    """Fresh import handle for interface module."""
    import tradingagents.dataflows.interface as iface

    return iface


def _reset_config(vendor_override=None, tool_vendors=None):
    """Patch get_config to return a controlled config dict."""
    import tradingagents.default_config as dc

    cfg = dc.DEFAULT_CONFIG.copy()
    cfg["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }
    cfg["tool_vendors"] = tool_vendors or {}
    if vendor_override:
        cfg["data_vendors"].update(vendor_override)
    return cfg


# ---------------------------------------------------------------------------
# TOOLS_CATEGORIES structure
# ---------------------------------------------------------------------------


def test_tools_categories_has_expected_categories():
    iface = _import_interface()
    expected = {"core_stock_apis", "technical_indicators", "fundamental_data", "news_data"}
    assert set(iface.TOOLS_CATEGORIES.keys()) == expected


def test_tools_categories_core_stock_apis_contains_get_stock_data():
    iface = _import_interface()
    assert "get_stock_data" in iface.TOOLS_CATEGORIES["core_stock_apis"]["tools"]


def test_tools_categories_technical_indicators_contains_get_indicators():
    iface = _import_interface()
    assert "get_indicators" in iface.TOOLS_CATEGORIES["technical_indicators"]["tools"]


def test_tools_categories_fundamental_data_tools():
    iface = _import_interface()
    tools = iface.TOOLS_CATEGORIES["fundamental_data"]["tools"]
    for expected in [
        "get_fundamentals",
        "get_balance_sheet",
        "get_cashflow",
        "get_income_statement",
    ]:
        assert expected in tools


def test_tools_categories_news_data_tools():
    iface = _import_interface()
    tools = iface.TOOLS_CATEGORIES["news_data"]["tools"]
    for expected in ["get_news", "get_global_news", "get_insider_transactions"]:
        assert expected in tools


# ---------------------------------------------------------------------------
# VENDOR_LIST
# ---------------------------------------------------------------------------


def test_vendor_list_contains_yfinance_and_alpha_vantage():
    iface = _import_interface()
    assert "yfinance" in iface.VENDOR_LIST
    assert "alpha_vantage" in iface.VENDOR_LIST


# ---------------------------------------------------------------------------
# VENDOR_METHODS mapping
# ---------------------------------------------------------------------------


def test_vendor_methods_contains_all_expected_methods():
    iface = _import_interface()
    expected_methods = [
        "get_stock_data",
        "get_indicators",
        "get_fundamentals",
        "get_balance_sheet",
        "get_cashflow",
        "get_income_statement",
        "get_news",
        "get_global_news",
        "get_insider_transactions",
    ]
    for method in expected_methods:
        assert method in iface.VENDOR_METHODS, f"Missing method: {method}"


def test_vendor_methods_each_has_yfinance_and_alpha_vantage():
    iface = _import_interface()
    for method, vendors in iface.VENDOR_METHODS.items():
        assert "yfinance" in vendors, f"{method} missing yfinance"
        assert "alpha_vantage" in vendors, f"{method} missing alpha_vantage"


def test_vendor_methods_values_are_callable():
    iface = _import_interface()
    for method, vendors in iface.VENDOR_METHODS.items():
        for vendor, impl in vendors.items():
            func = impl[0] if isinstance(impl, list) else impl
            assert callable(func), f"{method}/{vendor} implementation is not callable"


# ---------------------------------------------------------------------------
# get_category_for_method
# ---------------------------------------------------------------------------


def test_get_category_for_method_get_stock_data():
    iface = _import_interface()
    assert iface.get_category_for_method("get_stock_data") == "core_stock_apis"


def test_get_category_for_method_get_indicators():
    iface = _import_interface()
    assert iface.get_category_for_method("get_indicators") == "technical_indicators"


def test_get_category_for_method_fundamental_tools():
    iface = _import_interface()
    for tool in ["get_fundamentals", "get_balance_sheet", "get_cashflow", "get_income_statement"]:
        assert iface.get_category_for_method(tool) == "fundamental_data"


def test_get_category_for_method_news_tools():
    iface = _import_interface()
    for tool in ["get_news", "get_global_news", "get_insider_transactions"]:
        assert iface.get_category_for_method(tool) == "news_data"


def test_get_category_for_method_unknown_raises_value_error():
    iface = _import_interface()
    with pytest.raises(ValueError, match="not found in any category"):
        iface.get_category_for_method("nonexistent_tool")


# ---------------------------------------------------------------------------
# get_vendor
# ---------------------------------------------------------------------------


def test_get_vendor_returns_category_level_vendor():
    iface = _import_interface()
    cfg = _reset_config(vendor_override={"core_stock_apis": "alpha_vantage"})
    with patch("tradingagents.dataflows.interface.get_config", return_value=cfg):
        vendor = iface.get_vendor("core_stock_apis")
    assert vendor == "alpha_vantage"


def test_get_vendor_tool_level_takes_precedence_over_category():
    iface = _import_interface()
    cfg = _reset_config(
        vendor_override={"core_stock_apis": "yfinance"},
        tool_vendors={"get_stock_data": "alpha_vantage"},
    )
    with patch("tradingagents.dataflows.interface.get_config", return_value=cfg):
        vendor = iface.get_vendor("core_stock_apis", method="get_stock_data")
    assert vendor == "alpha_vantage"


def test_get_vendor_category_used_when_no_tool_override():
    iface = _import_interface()
    cfg = _reset_config(vendor_override={"core_stock_apis": "yfinance"}, tool_vendors={})
    with patch("tradingagents.dataflows.interface.get_config", return_value=cfg):
        vendor = iface.get_vendor("core_stock_apis", method="get_stock_data")
    assert vendor == "yfinance"


def test_get_vendor_returns_default_for_unknown_category():
    iface = _import_interface()
    cfg = _reset_config()
    with patch("tradingagents.dataflows.interface.get_config", return_value=cfg):
        vendor = iface.get_vendor("unknown_category")
    assert vendor == "default"


def test_get_vendor_no_method_ignores_tool_vendors():
    iface = _import_interface()
    cfg = _reset_config(
        vendor_override={"news_data": "yfinance"}, tool_vendors={"get_news": "alpha_vantage"}
    )
    with patch("tradingagents.dataflows.interface.get_config", return_value=cfg):
        # No method provided — should use category-level config
        vendor = iface.get_vendor("news_data")
    assert vendor == "yfinance"


# ---------------------------------------------------------------------------
# route_to_vendor — happy path
# ---------------------------------------------------------------------------


def test_route_to_vendor_calls_yfinance_implementation():
    iface = _import_interface()
    mock_fn = MagicMock(return_value="yfinance_result")
    cfg = _reset_config()  # default: yfinance for all categories

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_stock_data": {
                    "yfinance": mock_fn,
                    "alpha_vantage": MagicMock(),
                }
            },
        ),
    ):
        result = iface.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-12-31")

    mock_fn.assert_called_once_with("AAPL", "2024-01-01", "2024-12-31")
    assert result == "yfinance_result"


def test_route_to_vendor_calls_alpha_vantage_when_configured():
    iface = _import_interface()
    mock_av = MagicMock(return_value="av_result")
    cfg = _reset_config(vendor_override={"core_stock_apis": "alpha_vantage"})

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_stock_data": {
                    "yfinance": MagicMock(),
                    "alpha_vantage": mock_av,
                }
            },
        ),
    ):
        result = iface.route_to_vendor("get_stock_data", "TSLA", "2024-01-01", "2024-12-31")

    mock_av.assert_called_once_with("TSLA", "2024-01-01", "2024-12-31")
    assert result == "av_result"


def test_route_to_vendor_passes_kwargs():
    iface = _import_interface()
    mock_fn = MagicMock(return_value="ok")
    cfg = _reset_config()

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_indicators": {
                    "yfinance": mock_fn,
                    "alpha_vantage": MagicMock(),
                }
            },
        ),
    ):
        iface.route_to_vendor("get_indicators", "AAPL", indicator="RSI")

    mock_fn.assert_called_once_with("AAPL", indicator="RSI")


# ---------------------------------------------------------------------------
# route_to_vendor — fallback on AlphaVantageRateLimitError
# ---------------------------------------------------------------------------


def test_route_to_vendor_falls_back_on_rate_limit():
    iface = _import_interface()
    av_mock = MagicMock(side_effect=AlphaVantageRateLimitError("rate limited"))
    yf_mock = MagicMock(return_value="fallback_result")
    cfg = _reset_config(vendor_override={"core_stock_apis": "alpha_vantage"})

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_stock_data": {
                    "alpha_vantage": av_mock,
                    "yfinance": yf_mock,
                }
            },
        ),
    ):
        result = iface.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-12-31")

    assert result == "fallback_result"
    av_mock.assert_called_once()
    yf_mock.assert_called_once()


def test_route_to_vendor_does_not_fall_back_on_generic_exception():
    iface = _import_interface()
    av_mock = MagicMock(side_effect=RuntimeError("generic error"))
    yf_mock = MagicMock(return_value="should_not_reach")
    cfg = _reset_config(vendor_override={"core_stock_apis": "alpha_vantage"})

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_stock_data": {
                    "alpha_vantage": av_mock,
                    "yfinance": yf_mock,
                }
            },
        ),
    ):
        with pytest.raises(RuntimeError, match="generic error"):
            iface.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-12-31")

    yf_mock.assert_not_called()


# ---------------------------------------------------------------------------
# route_to_vendor — error cases
# ---------------------------------------------------------------------------


def test_route_to_vendor_raises_for_unknown_method():
    iface = _import_interface()
    with pytest.raises(ValueError, match="not found in any category"):
        iface.route_to_vendor("nonexistent_method")


def test_route_to_vendor_raises_runtime_error_when_all_vendors_exhausted():
    iface = _import_interface()
    av_mock = MagicMock(side_effect=AlphaVantageRateLimitError("rate limit"))
    yf_mock = MagicMock(side_effect=AlphaVantageRateLimitError("rate limit"))
    cfg = _reset_config(vendor_override={"core_stock_apis": "alpha_vantage"})

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_stock_data": {
                    "alpha_vantage": av_mock,
                    "yfinance": yf_mock,
                }
            },
        ),
    ):
        with pytest.raises(RuntimeError, match="No available vendor"):
            iface.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-12-31")


def test_route_to_vendor_skips_vendor_not_in_vendor_methods():
    iface = _import_interface()
    yf_mock = MagicMock(return_value="yf_result")
    # Config requests a vendor that doesn't exist in VENDOR_METHODS for this method
    cfg = _reset_config(vendor_override={"core_stock_apis": "nonexistent_vendor,yfinance"})

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_stock_data": {
                    "yfinance": yf_mock,
                    "alpha_vantage": MagicMock(),
                }
            },
        ),
    ):
        result = iface.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-12-31")

    assert result == "yf_result"


# ---------------------------------------------------------------------------
# Comma-separated vendor list (primary vendor chain)
# ---------------------------------------------------------------------------


def test_route_to_vendor_uses_first_in_comma_separated_list():
    iface = _import_interface()
    av_mock = MagicMock(return_value="av_result")
    yf_mock = MagicMock(return_value="yf_result")
    cfg = _reset_config(vendor_override={"core_stock_apis": "alpha_vantage,yfinance"})

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_stock_data": {
                    "alpha_vantage": av_mock,
                    "yfinance": yf_mock,
                }
            },
        ),
    ):
        result = iface.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-12-31")

    assert result == "av_result"
    yf_mock.assert_not_called()


def test_route_to_vendor_comma_list_falls_back_to_second_on_rate_limit():
    iface = _import_interface()
    av_mock = MagicMock(side_effect=AlphaVantageRateLimitError("limit"))
    yf_mock = MagicMock(return_value="yf_result")
    cfg = _reset_config(vendor_override={"core_stock_apis": "alpha_vantage,yfinance"})

    with (
        patch("tradingagents.dataflows.interface.get_config", return_value=cfg),
        patch.dict(
            iface.VENDOR_METHODS,
            {
                "get_stock_data": {
                    "alpha_vantage": av_mock,
                    "yfinance": yf_mock,
                }
            },
        ),
    ):
        result = iface.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-12-31")

    assert result == "yf_result"
