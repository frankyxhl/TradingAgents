"""Tests for tradingagents/dataflows/stockstats_utils.py

Covers: yf_retry, _clean_dataframe, load_ohlcv, filter_financials_by_date,
        StockstatsUtils.get_stock_stats
"""

from unittest.mock import MagicMock, call, patch

import numpy as np
import pandas as pd
import pytest
from yfinance.exceptions import YFRateLimitError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(rows=5, start="2024-01-02"):
    """Build a minimal OHLCV DataFrame with a 'Date' string column."""
    dates = pd.bdate_range(start, periods=rows)
    return pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "Open": [100.0 + i for i in range(rows)],
            "High": [105.0 + i for i in range(rows)],
            "Low": [99.0 + i for i in range(rows)],
            "Close": [103.0 + i for i in range(rows)],
            "Volume": [1_000_000 + i * 100_000 for i in range(rows)],
        }
    )


# ===================================================================
# yf_retry
# ===================================================================


class TestYfRetry:
    """Tests for the yf_retry exponential-backoff wrapper."""

    def test_success_on_first_attempt(self):
        from tradingagents.dataflows.stockstats_utils import yf_retry

        func = MagicMock(return_value="ok")
        assert yf_retry(func) == "ok"
        func.assert_called_once()

    @patch("tradingagents.dataflows.stockstats_utils.time.sleep")
    def test_retries_on_rate_limit_then_succeeds(self, mock_sleep):
        from tradingagents.dataflows.stockstats_utils import yf_retry

        func = MagicMock(side_effect=[YFRateLimitError(), "ok"])
        result = yf_retry(func, max_retries=3, base_delay=1.0)
        assert result == "ok"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(1.0)  # base_delay * 2^0

    @patch("tradingagents.dataflows.stockstats_utils.time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep):
        from tradingagents.dataflows.stockstats_utils import yf_retry

        func = MagicMock(side_effect=[YFRateLimitError(), YFRateLimitError(), "ok"])
        yf_retry(func, max_retries=3, base_delay=2.0)
        assert mock_sleep.call_args_list == [call(2.0), call(4.0)]

    @patch("tradingagents.dataflows.stockstats_utils.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        from tradingagents.dataflows.stockstats_utils import yf_retry

        func = MagicMock(side_effect=YFRateLimitError())
        with pytest.raises(YFRateLimitError):
            yf_retry(func, max_retries=2, base_delay=1.0)
        assert func.call_count == 3  # initial + 2 retries

    def test_non_rate_limit_error_propagates_immediately(self):
        from tradingagents.dataflows.stockstats_utils import yf_retry

        func = MagicMock(side_effect=ValueError("bad data"))
        with pytest.raises(ValueError, match="bad data"):
            yf_retry(func)
        func.assert_called_once()

    @patch("tradingagents.dataflows.stockstats_utils.time.sleep")
    def test_zero_max_retries_raises_on_first_failure(self, mock_sleep):
        from tradingagents.dataflows.stockstats_utils import yf_retry

        func = MagicMock(side_effect=YFRateLimitError())
        with pytest.raises(YFRateLimitError):
            yf_retry(func, max_retries=0)
        func.assert_called_once()
        mock_sleep.assert_not_called()


# ===================================================================
# _clean_dataframe
# ===================================================================


class TestCleanDataframe:
    """Tests for the _clean_dataframe helper."""

    def test_parses_date_column(self):
        from tradingagents.dataflows.stockstats_utils import _clean_dataframe

        df = _make_ohlcv(3)
        result = _clean_dataframe(df)
        assert pd.api.types.is_datetime64_any_dtype(result["Date"])

    def test_drops_rows_with_invalid_dates(self):
        from tradingagents.dataflows.stockstats_utils import _clean_dataframe

        df = _make_ohlcv(3)
        df.loc[1, "Date"] = "not-a-date"
        result = _clean_dataframe(df)
        assert len(result) == 2

    def test_drops_rows_with_nan_close(self):
        from tradingagents.dataflows.stockstats_utils import _clean_dataframe

        df = _make_ohlcv(3)
        df.loc[0, "Close"] = None
        result = _clean_dataframe(df)
        assert len(result) == 2

    def test_coerces_non_numeric_prices(self):
        from tradingagents.dataflows.stockstats_utils import _clean_dataframe

        dates = pd.bdate_range("2024-01-02", periods=3)
        df = pd.DataFrame(
            {
                "Date": dates.strftime("%Y-%m-%d"),
                "Open": ["bad", "101.0", "102.0"],  # first value non-numeric
                "High": [105.0, 106.0, 107.0],
                "Low": [99.0, 100.0, 101.0],
                "Close": [103.0, 104.0, 105.0],
                "Volume": [1_000_000, 1_100_000, 1_200_000],
            }
        )
        result = _clean_dataframe(df)
        # 'bad' coerced to NaN, then ffill/bfill should fill it
        assert not result["Open"].isna().any()

    def test_forward_and_back_fills_gaps(self):
        from tradingagents.dataflows.stockstats_utils import _clean_dataframe

        df = _make_ohlcv(5)
        df.loc[2, "Volume"] = None  # middle gap
        result = _clean_dataframe(df)
        assert not result["Volume"].isna().any()

    def test_empty_dataframe_returns_empty(self):
        from tradingagents.dataflows.stockstats_utils import _clean_dataframe

        df = pd.DataFrame(
            {"Date": [], "Open": [], "High": [], "Low": [], "Close": [], "Volume": []}
        )
        result = _clean_dataframe(df)
        assert result.empty

    def test_single_row(self):
        from tradingagents.dataflows.stockstats_utils import _clean_dataframe

        df = _make_ohlcv(1)
        result = _clean_dataframe(df)
        assert len(result) == 1

    def test_preserves_valid_data_unchanged(self):
        from tradingagents.dataflows.stockstats_utils import _clean_dataframe

        df = _make_ohlcv(3)
        result = _clean_dataframe(df)
        assert len(result) == 3
        assert list(result["Close"]) == [103.0, 104.0, 105.0]


# ===================================================================
# load_ohlcv
# ===================================================================


class TestLoadOhlcv:
    """Tests for load_ohlcv — all filesystem and network access mocked."""

    @patch("tradingagents.dataflows.stockstats_utils.os.path.exists", return_value=True)
    @patch("tradingagents.dataflows.stockstats_utils.pd.read_csv")
    @patch("tradingagents.dataflows.stockstats_utils.os.makedirs")
    @patch(
        "tradingagents.dataflows.stockstats_utils.get_config",
        return_value={"data_cache_dir": "/tmp/cache"},
    )
    def test_loads_from_cache_when_file_exists(
        self, mock_cfg, mock_makedirs, mock_read_csv, mock_exists
    ):
        from tradingagents.dataflows.stockstats_utils import load_ohlcv

        cached_df = _make_ohlcv(5)
        mock_read_csv.return_value = cached_df

        result = load_ohlcv("AAPL", "2024-01-08")
        mock_read_csv.assert_called_once()
        assert not result.empty

    @patch("tradingagents.dataflows.stockstats_utils.os.path.exists", return_value=False)
    @patch("tradingagents.dataflows.stockstats_utils.yf_retry")
    @patch("tradingagents.dataflows.stockstats_utils.os.makedirs")
    @patch(
        "tradingagents.dataflows.stockstats_utils.get_config",
        return_value={"data_cache_dir": "/tmp/cache"},
    )
    def test_downloads_when_no_cache(self, mock_cfg, mock_makedirs, mock_yf_retry, mock_exists):
        from tradingagents.dataflows.stockstats_utils import load_ohlcv

        raw_df = _make_ohlcv(5)
        # yf_retry returns reset_index() result; add Date col already
        mock_yf_retry.return_value = raw_df.set_index("Date")

        with patch.object(pd.DataFrame, "to_csv"):
            result = load_ohlcv("AAPL", "2024-01-08")

        mock_yf_retry.assert_called_once()
        assert not result.empty

    @patch("tradingagents.dataflows.stockstats_utils.os.path.exists", return_value=True)
    @patch("tradingagents.dataflows.stockstats_utils.pd.read_csv")
    @patch("tradingagents.dataflows.stockstats_utils.os.makedirs")
    @patch(
        "tradingagents.dataflows.stockstats_utils.get_config",
        return_value={"data_cache_dir": "/tmp/cache"},
    )
    def test_filters_future_dates(self, mock_cfg, mock_makedirs, mock_read_csv, mock_exists):
        from tradingagents.dataflows.stockstats_utils import load_ohlcv

        cached_df = _make_ohlcv(5, start="2024-01-02")
        mock_read_csv.return_value = cached_df

        # curr_date is 2024-01-03 => only first 2 rows should survive
        result = load_ohlcv("AAPL", "2024-01-03")
        assert len(result) == 2

    @patch("tradingagents.dataflows.stockstats_utils.os.path.exists", return_value=True)
    @patch("tradingagents.dataflows.stockstats_utils.pd.read_csv")
    @patch("tradingagents.dataflows.stockstats_utils.os.makedirs")
    @patch(
        "tradingagents.dataflows.stockstats_utils.get_config",
        return_value={"data_cache_dir": "/tmp/cache"},
    )
    def test_creates_cache_directory(self, mock_cfg, mock_makedirs, mock_read_csv, mock_exists):
        from tradingagents.dataflows.stockstats_utils import load_ohlcv

        mock_read_csv.return_value = _make_ohlcv(3)
        load_ohlcv("AAPL", "2024-01-04")
        mock_makedirs.assert_called_once_with("/tmp/cache", exist_ok=True)


# ===================================================================
# filter_financials_by_date
# ===================================================================


class TestFilterFinancialsByDate:
    """Tests for filter_financials_by_date."""

    def test_drops_future_columns(self):
        from tradingagents.dataflows.stockstats_utils import filter_financials_by_date

        df = pd.DataFrame({"2024-01-01": [1], "2024-06-01": [2], "2025-01-01": [3]})
        result = filter_financials_by_date(df, "2024-06-01")
        assert list(result.columns) == ["2024-01-01", "2024-06-01"]

    def test_keeps_all_columns_when_cutoff_is_far_future(self):
        from tradingagents.dataflows.stockstats_utils import filter_financials_by_date

        df = pd.DataFrame({"2024-01-01": [1], "2024-06-01": [2]})
        result = filter_financials_by_date(df, "2030-01-01")
        assert len(result.columns) == 2

    def test_returns_empty_df_unchanged(self):
        from tradingagents.dataflows.stockstats_utils import filter_financials_by_date

        df = pd.DataFrame()
        result = filter_financials_by_date(df, "2024-01-01")
        assert result.empty

    def test_returns_df_unchanged_when_no_curr_date(self):
        from tradingagents.dataflows.stockstats_utils import filter_financials_by_date

        df = pd.DataFrame({"2024-01-01": [1], "2025-01-01": [2]})
        result = filter_financials_by_date(df, "")
        assert len(result.columns) == 2

    def test_non_date_columns_are_dropped(self):
        from tradingagents.dataflows.stockstats_utils import filter_financials_by_date

        # Non-parseable columns get NaT from to_datetime, which is < cutoff => False
        df = pd.DataFrame({"revenue": [100], "2024-01-01": [200]})
        result = filter_financials_by_date(df, "2024-06-01")
        # 'revenue' cannot be parsed as a date: NaT <= cutoff is False, so dropped
        assert "revenue" not in result.columns
        assert "2024-01-01" in result.columns


# ===================================================================
# StockstatsUtils.get_stock_stats
# ===================================================================


class TestGetStockStats:
    """Tests for StockstatsUtils.get_stock_stats."""

    @patch("tradingagents.dataflows.stockstats_utils.load_ohlcv")
    def test_returns_indicator_value_for_trading_day(self, mock_load):
        from tradingagents.dataflows.stockstats_utils import StockstatsUtils

        df = _make_ohlcv(30, start="2024-01-02")
        # _clean_dataframe expects parsed dates downstream;
        # wrap() from stockstats will add indicators
        df["Date"] = pd.to_datetime(df["Date"])
        mock_load.return_value = df

        result = StockstatsUtils.get_stock_stats("AAPL", "close_10_sma", "2024-02-12")
        # Should return a numeric value (the SMA)
        assert isinstance(result, (int, float, np.floating))

    @patch("tradingagents.dataflows.stockstats_utils.load_ohlcv")
    def test_returns_na_for_non_trading_day(self, mock_load):
        from tradingagents.dataflows.stockstats_utils import StockstatsUtils

        df = _make_ohlcv(5, start="2024-01-02")
        df["Date"] = pd.to_datetime(df["Date"])
        mock_load.return_value = df

        # 2024-01-01 is not in the data (holiday / before start)
        result = StockstatsUtils.get_stock_stats("AAPL", "close_10_sma", "2024-01-01")
        assert result == "N/A: Not a trading day (weekend or holiday)"

    @patch("tradingagents.dataflows.stockstats_utils.load_ohlcv")
    def test_calls_load_ohlcv_with_correct_args(self, mock_load):
        from tradingagents.dataflows.stockstats_utils import StockstatsUtils

        df = _make_ohlcv(30, start="2024-01-02")
        df["Date"] = pd.to_datetime(df["Date"])
        mock_load.return_value = df

        StockstatsUtils.get_stock_stats("MSFT", "close_10_sma", "2024-02-12")
        mock_load.assert_called_once_with("MSFT", "2024-02-12")

    @patch("tradingagents.dataflows.stockstats_utils.load_ohlcv")
    def test_rsi_indicator(self, mock_load):
        from tradingagents.dataflows.stockstats_utils import StockstatsUtils

        # Need enough rows for RSI calculation (typically 14 periods)
        df = _make_ohlcv(30, start="2024-01-02")
        df["Date"] = pd.to_datetime(df["Date"])
        mock_load.return_value = df

        result = StockstatsUtils.get_stock_stats("AAPL", "rsi_14", "2024-02-12")
        assert isinstance(result, (int, float, np.floating))
        # RSI should be between 0 and 100
        assert 0 <= result <= 100

    @patch("tradingagents.dataflows.stockstats_utils.load_ohlcv")
    def test_macd_indicator(self, mock_load):
        from tradingagents.dataflows.stockstats_utils import StockstatsUtils

        df = _make_ohlcv(30, start="2024-01-02")
        df["Date"] = pd.to_datetime(df["Date"])
        mock_load.return_value = df

        result = StockstatsUtils.get_stock_stats("AAPL", "macd", "2024-02-12")
        assert isinstance(result, (int, float, np.floating))
