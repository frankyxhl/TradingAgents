"""Tests for tradingagents/dataflows/y_finance.py

All yfinance / network calls are mocked. No real HTTP requests are made.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_ohlcv_df(n=5, start="2024-01-02", tz="US/Eastern"):
    """Return a realistic OHLCV DataFrame with timezone-aware DatetimeIndex."""
    idx = pd.bdate_range(start=start, periods=n, tz=tz)
    return pd.DataFrame(
        {
            "Open":  [100.0 + i for i in range(n)],
            "High":  [105.0 + i for i in range(n)],
            "Low":   [99.0  + i for i in range(n)],
            "Close": [103.0 + i for i in range(n)],
            "Volume": [1_000_000 + i * 100_000 for i in range(n)],
        },
        index=idx,
    )


def _make_financials_df():
    """Return a small DataFrame mimicking yfinance balance sheet / income stmt."""
    cols = [pd.Timestamp("2024-06-30"), pd.Timestamp("2024-03-31")]
    return pd.DataFrame(
        {"TotalAssets": [100, 200], "TotalLiabilities": [50, 80]},
        index=["Row1", "Row2"],
    ).T
    # Transpose so dates are columns (like yfinance financial statements)


def _make_financials_df_with_dates():
    """Return a DataFrame that mimics yfinance financial statements (dates as columns)."""
    dates = [pd.Timestamp("2024-06-30"), pd.Timestamp("2024-03-31"), pd.Timestamp("2023-12-31")]
    data = {d: [100 + i, 200 + i] for i, d in enumerate(dates)}
    return pd.DataFrame(data, index=["TotalAssets", "TotalLiabilities"])


# ============================================================================
# get_YFin_data_online
# ============================================================================

class TestGetYFinDataOnline:

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_csv_with_header(self, mock_ticker_cls, mock_retry):
        """Normal case: returns a header + CSV string."""
        df = _make_ohlcv_df(n=3)
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_YFin_data_online

        result = get_YFin_data_online("AAPL", "2024-01-01", "2024-01-10")

        assert "# Stock data for AAPL" in result
        assert "# Total records: 3" in result
        # CSV body should contain Open, Close, etc.
        assert "Open" in result
        assert "Close" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_empty_data_returns_message(self, mock_ticker_cls, mock_retry):
        """When yfinance returns an empty DataFrame, return a human-readable message."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: pd.DataFrame()

        from tradingagents.dataflows.y_finance import get_YFin_data_online

        result = get_YFin_data_online("XYZ", "2024-01-01", "2024-01-10")
        assert "No data found" in result
        assert "XYZ" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_timezone_stripped_from_index(self, mock_ticker_cls, mock_retry):
        """Timezone info should be removed from the index."""
        df = _make_ohlcv_df(n=2, tz="US/Eastern")
        assert df.index.tz is not None  # precondition
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_YFin_data_online

        result = get_YFin_data_online("AAPL", "2024-01-01", "2024-01-10")
        # Should NOT contain timezone abbreviation in the CSV dates
        assert "US/Eastern" not in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_numeric_columns_rounded(self, mock_ticker_cls, mock_retry):
        """Numeric columns should be rounded to 2 decimal places."""
        df = pd.DataFrame(
            {
                "Open": [100.12345],
                "High": [105.6789],
                "Low": [99.999],
                "Close": [103.111],
                "Adj Close": [102.5555],
                "Volume": [1_000_000],
            },
            index=pd.date_range("2024-01-02", periods=1),
        )
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_YFin_data_online

        result = get_YFin_data_online("AAPL", "2024-01-01", "2024-01-05")
        assert "100.12" in result
        assert "105.68" in result
        assert "102.56" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_no_tz_index_left_alone(self, mock_ticker_cls, mock_retry):
        """If data has no timezone, code should not error out."""
        df = _make_ohlcv_df(n=2, tz=None)
        assert df.index.tz is None
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_YFin_data_online

        result = get_YFin_data_online("MSFT", "2024-01-01", "2024-01-10")
        assert "# Stock data for MSFT" in result

    def test_invalid_date_format_raises(self):
        """Passing a malformed date should raise ValueError from strptime."""
        from tradingagents.dataflows.y_finance import get_YFin_data_online

        with pytest.raises(ValueError):
            get_YFin_data_online("AAPL", "not-a-date", "2024-01-10")

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_symbol_uppercased(self, mock_ticker_cls, mock_retry):
        """The symbol should be uppercased for the Ticker constructor and in the header."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: pd.DataFrame()

        from tradingagents.dataflows.y_finance import get_YFin_data_online

        get_YFin_data_online("aapl", "2024-01-01", "2024-01-10")
        mock_ticker_cls.assert_called_once_with("AAPL")


# ============================================================================
# get_stock_stats_indicators_window
# ============================================================================

class TestGetStockStatsIndicatorsWindow:

    def test_unsupported_indicator_raises(self):
        """Passing an unsupported indicator name should raise ValueError."""
        from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

        with pytest.raises(ValueError, match="not supported"):
            get_stock_stats_indicators_window("AAPL", "fake_indicator", "2024-06-01", 5)

    @patch("tradingagents.dataflows.y_finance._get_stock_stats_bulk")
    def test_bulk_path_returns_date_values(self, mock_bulk):
        """When bulk succeeds, result should contain date-value pairs."""
        mock_bulk.return_value = {
            "2024-06-01": "103.5",
            "2024-05-31": "102.0",
            "2024-05-30": "101.0",
        }

        from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

        result = get_stock_stats_indicators_window("AAPL", "rsi", "2024-06-01", 3)

        assert "2024-06-01: 103.5" in result
        assert "2024-05-31: 102.0" in result
        assert "rsi" in result.lower() or "RSI" in result

    @patch("tradingagents.dataflows.y_finance._get_stock_stats_bulk")
    def test_missing_dates_show_not_trading_day(self, mock_bulk):
        """Dates not in bulk data (weekends) should show N/A message."""
        # Only provide weekday data; Saturday 2024-06-01 is a Saturday? No,
        # let's just provide data for one day and check another day is N/A.
        mock_bulk.return_value = {
            "2024-06-03": "105.0",  # Monday
        }

        from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

        result = get_stock_stats_indicators_window("AAPL", "rsi", "2024-06-03", 3)

        # 2024-06-02 (Sunday) and 2024-06-01 (Saturday) should be N/A
        assert "N/A: Not a trading day" in result

    @patch("tradingagents.dataflows.y_finance._get_stock_stats_bulk")
    def test_header_contains_date_range(self, mock_bulk):
        """Result header should show the indicator name and date range."""
        mock_bulk.return_value = {}

        from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

        result = get_stock_stats_indicators_window("AAPL", "macd", "2024-06-10", 5)

        assert "## macd values from" in result
        assert "2024-06-10" in result

    @patch("tradingagents.dataflows.y_finance._get_stock_stats_bulk")
    def test_description_appended_for_known_indicator(self, mock_bulk):
        """The description for a known indicator should be appended."""
        mock_bulk.return_value = {}

        from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

        result = get_stock_stats_indicators_window("AAPL", "rsi", "2024-06-01", 1)
        assert "RSI" in result
        assert "overbought" in result.lower() or "oversold" in result.lower()

    @patch("tradingagents.dataflows.y_finance.get_stockstats_indicator")
    @patch("tradingagents.dataflows.y_finance._get_stock_stats_bulk", side_effect=Exception("bulk error"))
    def test_fallback_to_individual_calls_on_bulk_failure(self, mock_bulk, mock_individual):
        """When _get_stock_stats_bulk raises, the function falls back to per-date calls."""
        mock_individual.return_value = "99.5"

        from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

        result = get_stock_stats_indicators_window("AAPL", "rsi", "2024-06-03", 2)

        # The fallback should have called get_stockstats_indicator for each date
        assert mock_individual.call_count >= 2
        assert "99.5" in result


# ============================================================================
# _get_stock_stats_bulk
# ============================================================================

class TestGetStockStatsBulk:
    """Tests for _get_stock_stats_bulk.

    NOTE: The source file has a bug -- `pd.isna()` is called on line 213 but
    `pandas` is never imported as `pd` in y_finance.py.  This causes a
    NameError at runtime.  The bug is masked in production because the caller
    (get_stock_stats_indicators_window) wraps the call in try/except and
    falls back to per-date calls.  The tests below verify the bug exists
    (NameError is raised) so we don't silently hide it.
    """

    @patch("tradingagents.dataflows.y_finance.load_ohlcv")
    def test_raises_name_error_due_to_missing_pd_import(self, mock_load):
        """_get_stock_stats_bulk raises NameError because `pd` is not imported.

        This documents a real bug: the function uses `pd.isna()` but does
        not import pandas.  If the bug is fixed (by adding `import pandas as pd`
        to y_finance.py), this test should be updated to verify correct output.
        """
        df = pd.DataFrame({
            "Date": pd.to_datetime(["2024-06-01", "2024-06-02", "2024-06-03"]),
            "Open": [100, 101, 102],
            "High": [105, 106, 107],
            "Low": [99, 100, 101],
            "Close": [103, 104, 105],
            "Volume": [1e6, 1.1e6, 1.2e6],
        })
        mock_load.return_value = df

        from tradingagents.dataflows.y_finance import _get_stock_stats_bulk

        with pytest.raises(NameError, match="pd"):
            _get_stock_stats_bulk("AAPL", "close_10_ema", "2024-06-03")

    @patch("tradingagents.dataflows.y_finance.load_ohlcv")
    def test_calls_load_ohlcv_and_wraps(self, mock_load):
        """Verify load_ohlcv is called and stockstats wrap is used before the bug hits."""
        df = pd.DataFrame({
            "Date": pd.to_datetime(["2024-06-01"]),
            "Open": [100],
            "High": [105],
            "Low": [99],
            "Close": [103],
            "Volume": [1e6],
        })
        mock_load.return_value = df

        from tradingagents.dataflows.y_finance import _get_stock_stats_bulk

        # Will raise NameError due to pd.isna bug, but load_ohlcv should have been called
        with pytest.raises(NameError):
            _get_stock_stats_bulk("AAPL", "close_10_ema", "2024-06-01")

        mock_load.assert_called_once_with("AAPL", "2024-06-01")


# ============================================================================
# get_stockstats_indicator
# ============================================================================

class TestGetStockstatsIndicator:

    @patch("tradingagents.dataflows.y_finance.StockstatsUtils")
    def test_returns_stringified_value(self, mock_utils):
        """Normal case: returns the indicator value as a string."""
        mock_utils.get_stock_stats.return_value = 72.5

        from tradingagents.dataflows.y_finance import get_stockstats_indicator

        result = get_stockstats_indicator("AAPL", "rsi", "2024-06-03")
        assert result == "72.5"

    @patch("tradingagents.dataflows.y_finance.StockstatsUtils")
    def test_returns_empty_string_on_exception(self, mock_utils):
        """On exception, should return an empty string."""
        mock_utils.get_stock_stats.side_effect = RuntimeError("API error")

        from tradingagents.dataflows.y_finance import get_stockstats_indicator

        result = get_stockstats_indicator("AAPL", "rsi", "2024-06-03")
        assert result == ""

    @patch("tradingagents.dataflows.y_finance.StockstatsUtils")
    def test_normalizes_date_format(self, mock_utils):
        """The function parses and re-formats the date via strptime/strftime."""
        mock_utils.get_stock_stats.return_value = "100"

        from tradingagents.dataflows.y_finance import get_stockstats_indicator

        get_stockstats_indicator("AAPL", "rsi", "2024-06-03")
        # StockstatsUtils should receive the normalized date
        call_args = mock_utils.get_stock_stats.call_args
        assert call_args[0][2] == "2024-06-03"


# ============================================================================
# get_fundamentals
# ============================================================================

class TestGetFundamentals:

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_formatted_fundamentals(self, mock_ticker_cls, mock_retry):
        """Normal case: returns header + key-value lines."""
        mock_info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "marketCap": 3_000_000_000_000,
            "trailingPE": 28.5,
        }
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: mock_info

        from tradingagents.dataflows.y_finance import get_fundamentals

        result = get_fundamentals("AAPL")

        assert "# Company Fundamentals for AAPL" in result
        assert "Name: Apple Inc." in result
        assert "Sector: Technology" in result
        assert "Market Cap: 3000000000000" in result
        assert "PE Ratio (TTM): 28.5" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_empty_info_returns_message(self, mock_ticker_cls, mock_retry):
        """When info dict is empty/falsy, return a not-found message."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: {}

        from tradingagents.dataflows.y_finance import get_fundamentals

        result = get_fundamentals("XYZ")
        assert "No fundamentals data found" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_none_info_returns_message(self, mock_ticker_cls, mock_retry):
        """When info is None, return a not-found message."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: None

        from tradingagents.dataflows.y_finance import get_fundamentals

        result = get_fundamentals("XYZ")
        assert "No fundamentals data found" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_missing_fields_omitted(self, mock_ticker_cls, mock_retry):
        """Fields with None values should be omitted from output."""
        mock_info = {
            "longName": "Test Corp",
            "sector": None,
            "marketCap": 1_000_000,
        }
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: mock_info

        from tradingagents.dataflows.y_finance import get_fundamentals

        result = get_fundamentals("TEST")
        assert "Name: Test Corp" in result
        assert "Market Cap: 1000000" in result
        assert "Sector:" not in result

    @patch("tradingagents.dataflows.y_finance.yf.Ticker", side_effect=Exception("connection error"))
    def test_exception_returns_error_message(self, mock_ticker_cls):
        """On exception, should return an error string."""
        from tradingagents.dataflows.y_finance import get_fundamentals

        result = get_fundamentals("AAPL")
        assert "Error retrieving fundamentals" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_symbol_uppercased(self, mock_ticker_cls, mock_retry):
        """Symbol should be uppercased."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: {}

        from tradingagents.dataflows.y_finance import get_fundamentals

        get_fundamentals("aapl")
        mock_ticker_cls.assert_called_with("AAPL")


# ============================================================================
# get_balance_sheet
# ============================================================================

class TestGetBalanceSheet:

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: d)
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_quarterly_balance_sheet(self, mock_ticker_cls, mock_retry, mock_filter):
        """Quarterly frequency should use quarterly_balance_sheet."""
        df = _make_financials_df_with_dates()
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_balance_sheet

        result = get_balance_sheet("AAPL", freq="quarterly", curr_date="2024-06-30")
        assert "# Balance Sheet data for AAPL (quarterly)" in result

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: d)
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_annual_balance_sheet(self, mock_ticker_cls, mock_retry, mock_filter):
        """Annual frequency should use balance_sheet."""
        df = _make_financials_df_with_dates()
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_balance_sheet

        result = get_balance_sheet("AAPL", freq="annual", curr_date="2024-06-30")
        assert "# Balance Sheet data for AAPL (annual)" in result

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: pd.DataFrame())
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_empty_returns_message(self, mock_ticker_cls, mock_retry, mock_filter):
        """Empty data should return a not-found message."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: pd.DataFrame()

        from tradingagents.dataflows.y_finance import get_balance_sheet

        result = get_balance_sheet("XYZ")
        assert "No balance sheet data found" in result

    @patch("tradingagents.dataflows.y_finance.yf.Ticker", side_effect=Exception("fail"))
    def test_exception_returns_error(self, mock_ticker_cls):
        """On exception, return an error string."""
        from tradingagents.dataflows.y_finance import get_balance_sheet

        result = get_balance_sheet("AAPL")
        assert "Error retrieving balance sheet" in result


# ============================================================================
# get_cashflow
# ============================================================================

class TestGetCashflow:

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: d)
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_quarterly_cashflow(self, mock_ticker_cls, mock_retry, mock_filter):
        """Quarterly frequency should use quarterly_cashflow."""
        df = _make_financials_df_with_dates()
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_cashflow

        result = get_cashflow("AAPL", freq="quarterly", curr_date="2024-06-30")
        assert "# Cash Flow data for AAPL (quarterly)" in result

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: d)
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_annual_cashflow(self, mock_ticker_cls, mock_retry, mock_filter):
        """Annual frequency should use cashflow."""
        df = _make_financials_df_with_dates()
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_cashflow

        result = get_cashflow("AAPL", freq="annual", curr_date="2024-06-30")
        assert "# Cash Flow data for AAPL (annual)" in result

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: pd.DataFrame())
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_empty_returns_message(self, mock_ticker_cls, mock_retry, mock_filter):
        """Empty data should return a not-found message."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: pd.DataFrame()

        from tradingagents.dataflows.y_finance import get_cashflow

        result = get_cashflow("XYZ")
        assert "No cash flow data found" in result

    @patch("tradingagents.dataflows.y_finance.yf.Ticker", side_effect=Exception("fail"))
    def test_exception_returns_error(self, mock_ticker_cls):
        """On exception, return an error string."""
        from tradingagents.dataflows.y_finance import get_cashflow

        result = get_cashflow("AAPL")
        assert "Error retrieving cash flow" in result


# ============================================================================
# get_income_statement
# ============================================================================

class TestGetIncomeStatement:

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: d)
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_quarterly_income(self, mock_ticker_cls, mock_retry, mock_filter):
        """Quarterly frequency should use quarterly_income_stmt."""
        df = _make_financials_df_with_dates()
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_income_statement

        result = get_income_statement("AAPL", freq="quarterly", curr_date="2024-06-30")
        assert "# Income Statement data for AAPL (quarterly)" in result

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: d)
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_annual_income(self, mock_ticker_cls, mock_retry, mock_filter):
        """Annual frequency should use income_stmt."""
        df = _make_financials_df_with_dates()
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_income_statement

        result = get_income_statement("AAPL", freq="annual", curr_date="2024-06-30")
        assert "# Income Statement data for AAPL (annual)" in result

    @patch("tradingagents.dataflows.y_finance.filter_financials_by_date", side_effect=lambda d, c: pd.DataFrame())
    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_empty_returns_message(self, mock_ticker_cls, mock_retry, mock_filter):
        """Empty data should return a not-found message."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: pd.DataFrame()

        from tradingagents.dataflows.y_finance import get_income_statement

        result = get_income_statement("XYZ")
        assert "No income statement data found" in result

    @patch("tradingagents.dataflows.y_finance.yf.Ticker", side_effect=Exception("fail"))
    def test_exception_returns_error(self, mock_ticker_cls):
        """On exception, return an error string."""
        from tradingagents.dataflows.y_finance import get_income_statement

        result = get_income_statement("AAPL")
        assert "Error retrieving income statement" in result


# ============================================================================
# get_insider_transactions
# ============================================================================

class TestGetInsiderTransactions:

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_returns_csv_with_header(self, mock_ticker_cls, mock_retry):
        """Normal case: returns a header + CSV string of transactions."""
        df = pd.DataFrame({
            "Insider": ["John Doe", "Jane Smith"],
            "Shares": [1000, -500],
            "Value": [150000, -75000],
        })
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: df

        from tradingagents.dataflows.y_finance import get_insider_transactions

        result = get_insider_transactions("AAPL")
        assert "# Insider Transactions data for AAPL" in result
        assert "John Doe" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_empty_returns_message(self, mock_ticker_cls, mock_retry):
        """Empty DataFrame should return a not-found message."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: pd.DataFrame()

        from tradingagents.dataflows.y_finance import get_insider_transactions

        result = get_insider_transactions("XYZ")
        assert "No insider transactions data found" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_none_returns_message(self, mock_ticker_cls, mock_retry):
        """None data should return a not-found message."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: None

        from tradingagents.dataflows.y_finance import get_insider_transactions

        result = get_insider_transactions("XYZ")
        assert "No insider transactions data found" in result

    @patch("tradingagents.dataflows.y_finance.yf.Ticker", side_effect=Exception("fail"))
    def test_exception_returns_error(self, mock_ticker_cls):
        """On exception, return an error string."""
        from tradingagents.dataflows.y_finance import get_insider_transactions

        result = get_insider_transactions("AAPL")
        assert "Error retrieving insider transactions" in result

    @patch("tradingagents.dataflows.y_finance.yf_retry")
    @patch("tradingagents.dataflows.y_finance.yf.Ticker")
    def test_symbol_uppercased(self, mock_ticker_cls, mock_retry):
        """Symbol should be uppercased."""
        mock_ticker_inst = MagicMock()
        mock_ticker_cls.return_value = mock_ticker_inst
        mock_retry.side_effect = lambda fn: None

        from tradingagents.dataflows.y_finance import get_insider_transactions

        get_insider_transactions("msft")
        mock_ticker_cls.assert_called_with("MSFT")


# ============================================================================
# Supported indicators list coverage
# ============================================================================

class TestSupportedIndicators:
    """Ensure all documented indicators are accepted."""

    SUPPORTED = [
        "close_50_sma", "close_200_sma", "close_10_ema",
        "macd", "macds", "macdh",
        "rsi",
        "boll", "boll_ub", "boll_lb", "atr",
        "vwma", "mfi",
    ]

    @patch("tradingagents.dataflows.y_finance._get_stock_stats_bulk")
    @pytest.mark.parametrize("indicator", SUPPORTED)
    def test_all_known_indicators_accepted(self, mock_bulk, indicator):
        """Each known indicator should not raise ValueError."""
        mock_bulk.return_value = {}

        from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

        result = get_stock_stats_indicators_window("AAPL", indicator, "2024-06-01", 1)
        assert f"## {indicator} values from" in result
