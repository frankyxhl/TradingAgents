"""Tests for LVM-2005: interactive chart tab in HTML report."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _make_hist(n=20):
    """Create a mock yfinance history DataFrame."""
    idx = pd.bdate_range("2024-01-02", periods=n)
    return pd.DataFrame(
        {
            "Open": [100 + i for i in range(n)],
            "High": [105 + i for i in range(n)],
            "Low": [99 + i for i in range(n)],
            "Close": [103 + i for i in range(n)],
            "Volume": [1000000 + i * 100000 for i in range(n)],
        },
        index=idx,
    )


def _make_graph():
    """Create a TradingAgentsGraph instance without __init__."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    return TradingAgentsGraph.__new__(TradingAgentsGraph)


# ---------------------------------------------------------------------------
# _fetch_ohlcv tests
# ---------------------------------------------------------------------------


@patch("tradingagents.dataflows.stockstats_utils.yf_retry")
@patch("yfinance.Ticker")
def test_fetch_ohlcv_returns_daily_and_weekly(mock_ticker_cls, mock_retry):
    hist = _make_hist(10)
    mock_retry.side_effect = lambda fn: fn()
    mock_ticker_cls.return_value.history.return_value = hist

    graph = _make_graph()
    daily, weekly = graph._fetch_ohlcv("AAPL", "2025-01-15")

    assert len(daily) == 10
    assert len(weekly) < len(daily)
    # Check dict keys
    for key in ("time", "open", "high", "low", "close", "volume"):
        assert key in daily[0]


@patch("tradingagents.dataflows.stockstats_utils.yf_retry")
def test_fetch_ohlcv_failure_returns_empty(mock_retry):
    mock_retry.side_effect = Exception("network error")

    graph = _make_graph()
    daily, weekly = graph._fetch_ohlcv("AAPL", "2025-01-15")

    assert daily == []
    assert weekly == []


@patch("tradingagents.dataflows.stockstats_utils.yf_retry")
@patch("yfinance.Ticker")
def test_fetch_ohlcv_empty_dataframe_returns_empty(mock_ticker_cls, mock_retry):
    mock_retry.side_effect = lambda fn: fn()
    mock_ticker_cls.return_value.history.return_value = pd.DataFrame()

    graph = _make_graph()
    daily, weekly = graph._fetch_ohlcv("AAPL", "2025-01-15")

    assert daily == []
    assert weekly == []


@patch("tradingagents.dataflows.stockstats_utils.yf_retry")
@patch("yfinance.Ticker")
def test_fetch_ohlcv_passes_end_date(mock_ticker_cls, mock_retry):
    hist = _make_hist(5)
    mock_retry.side_effect = lambda fn: fn()
    mock_ticker_cls.return_value.history.return_value = hist

    graph = _make_graph()
    graph._fetch_ohlcv("AAPL", "2025-01-15")

    mock_ticker_cls.return_value.history.assert_called_once()
    call_kwargs = mock_ticker_cls.return_value.history.call_args
    assert call_kwargs[1]["end"] == "2025-01-15" or call_kwargs.kwargs["end"] == "2025-01-15"


@patch("tradingagents.dataflows.stockstats_utils.yf_retry")
@patch("yfinance.Ticker")
def test_fetch_ohlcv_weekly_fewer_than_daily(mock_ticker_cls, mock_retry):
    hist = _make_hist(20)
    mock_retry.side_effect = lambda fn: fn()
    mock_ticker_cls.return_value.history.return_value = hist

    graph = _make_graph()
    daily, weekly = graph._fetch_ohlcv("AAPL", "2025-01-15")

    assert len(daily) == 20
    assert len(weekly) < len(daily)


# ---------------------------------------------------------------------------
# render_html tests
# ---------------------------------------------------------------------------


def _base_data(**overrides):
    """Minimal data dict for render_html."""
    data = {
        "company_of_interest": "TEST",
        "trade_date": "2026-04-04",
        "market_report": "test market",
        "sentiment_report": "test sentiment",
        "news_report": "test news",
        "fundamentals_report": "test fundamentals",
        "final_trade_decision": "HOLD",
    }
    data.update(overrides)
    return data


def test_render_html_with_ohlcv_includes_chart():
    from tradingagents.render_report import render_html

    data = _base_data(
        ohlcv_daily=[
            {
                "time": "2024-01-02",
                "open": 100,
                "high": 105,
                "low": 99,
                "close": 103,
                "volume": 1000000,
            }
        ],
        ohlcv_weekly=[
            {
                "time": "2024-01-05",
                "open": 100,
                "high": 105,
                "low": 99,
                "close": 103,
                "volume": 5000000,
            }
        ],
    )
    html = render_html(data)
    assert "tab-chart" in html
    assert "LightweightCharts" in html
    assert "tab-analysis" in html


def test_render_html_without_ohlcv_no_chart():
    from tradingagents.render_report import render_html

    data = _base_data(ohlcv_daily=[], ohlcv_weekly=[])
    html = render_html(data)
    assert "tab-chart" not in html


def test_render_html_backward_compatible():
    from tradingagents.render_report import render_html

    # No ohlcv keys at all
    data = _base_data()
    html = render_html(data)
    assert "<!DOCTYPE html>" in html
    assert "tab-chart" not in html
    assert "tab-analysis" in html


def test_pdf_css_hides_chart():
    from tradingagents.render_report import _PDF_CSS

    assert "#tab-chart" in _PDF_CSS
    assert "display: none" in _PDF_CSS
    assert "#tab-analysis" in _PDF_CSS
