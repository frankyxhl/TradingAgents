"""Tests for tradingagents/dataflows/yfinance_news.py"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from tradingagents.dataflows.yfinance_news import (
    _extract_article_data,
    get_news_yfinance,
    get_global_news_yfinance,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _nested_article(
    title="Stock rises 10%",
    summary="Great quarter results",
    publisher="Reuters",
    url="https://example.com/article1",
    pub_date="2024-01-15T12:00:00Z",
):
    """Build a yfinance article dict with nested 'content' structure."""
    article = {
        "content": {
            "title": title,
            "summary": summary,
            "provider": {"displayName": publisher},
            "canonicalUrl": {"url": url},
            "pubDate": pub_date,
        }
    }
    return article


def _flat_article(
    title="Earnings beat expectations",
    summary="",
    publisher="Bloomberg",
    link="https://example.com/article2",
):
    """Build a yfinance article dict with flat structure (no 'content' key)."""
    return {
        "title": title,
        "summary": summary,
        "publisher": publisher,
        "link": link,
    }


# ---------------------------------------------------------------------------
# _extract_article_data — nested content structure
# ---------------------------------------------------------------------------

class TestExtractArticleDataNested:
    """Tests for _extract_article_data with nested 'content' structure."""

    def test_extracts_title(self):
        data = _extract_article_data(_nested_article(title="Big News"))
        assert data["title"] == "Big News"

    def test_extracts_summary(self):
        data = _extract_article_data(_nested_article(summary="A detailed summary"))
        assert data["summary"] == "A detailed summary"

    def test_extracts_publisher_from_provider(self):
        data = _extract_article_data(_nested_article(publisher="CNBC"))
        assert data["publisher"] == "CNBC"

    def test_extracts_link_from_canonical_url(self):
        data = _extract_article_data(_nested_article(url="https://example.com/news"))
        assert data["link"] == "https://example.com/news"

    def test_extracts_link_from_click_through_url_fallback(self):
        article = {
            "content": {
                "title": "Test",
                "summary": "",
                "provider": {"displayName": "AP"},
                "clickThroughUrl": {"url": "https://click.example.com"},
                "pubDate": "",
            }
        }
        data = _extract_article_data(article)
        assert data["link"] == "https://click.example.com"

    def test_link_empty_when_no_url_objects(self):
        article = {
            "content": {
                "title": "Test",
                "summary": "",
                "provider": {"displayName": "AP"},
                "pubDate": "",
            }
        }
        data = _extract_article_data(article)
        assert data["link"] == ""

    def test_parses_pub_date_iso_with_z_suffix(self):
        data = _extract_article_data(_nested_article(pub_date="2024-01-15T12:00:00Z"))
        assert data["pub_date"] is not None
        assert data["pub_date"].year == 2024
        assert data["pub_date"].month == 1
        assert data["pub_date"].day == 15

    def test_parses_pub_date_iso_with_offset(self):
        data = _extract_article_data(
            _nested_article(pub_date="2024-06-01T08:30:00+05:00")
        )
        assert data["pub_date"] is not None
        assert data["pub_date"].year == 2024
        assert data["pub_date"].month == 6

    def test_pub_date_none_when_empty_string(self):
        data = _extract_article_data(_nested_article(pub_date=""))
        assert data["pub_date"] is None

    def test_pub_date_none_when_malformed(self):
        data = _extract_article_data(_nested_article(pub_date="not-a-date"))
        assert data["pub_date"] is None

    def test_defaults_when_fields_missing(self):
        article = {"content": {}}
        data = _extract_article_data(article)
        assert data["title"] == "No title"
        assert data["summary"] == ""
        assert data["publisher"] == "Unknown"
        assert data["link"] == ""
        assert data["pub_date"] is None


# ---------------------------------------------------------------------------
# _extract_article_data — flat structure
# ---------------------------------------------------------------------------

class TestExtractArticleDataFlat:
    """Tests for _extract_article_data with flat (non-nested) structure."""

    def test_extracts_title(self):
        data = _extract_article_data(_flat_article(title="Flat Title"))
        assert data["title"] == "Flat Title"

    def test_extracts_publisher(self):
        data = _extract_article_data(_flat_article(publisher="WSJ"))
        assert data["publisher"] == "WSJ"

    def test_extracts_link(self):
        data = _extract_article_data(_flat_article(link="https://wsj.com"))
        assert data["link"] == "https://wsj.com"

    def test_pub_date_always_none(self):
        data = _extract_article_data(_flat_article())
        assert data["pub_date"] is None

    def test_defaults_when_fields_missing(self):
        data = _extract_article_data({})
        assert data["title"] == "No title"
        assert data["summary"] == ""
        assert data["publisher"] == "Unknown"
        assert data["link"] == ""
        assert data["pub_date"] is None


# ---------------------------------------------------------------------------
# get_news_yfinance
# ---------------------------------------------------------------------------

class TestGetNewsYfinance:
    """Tests for get_news_yfinance function."""

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_returns_formatted_news(self, mock_retry, mock_ticker_cls):
        articles = [
            _nested_article(
                title="AAPL up 5%",
                summary="Strong earnings",
                publisher="Reuters",
                url="https://r.com/1",
                pub_date="2024-01-15T10:00:00Z",
            ),
        ]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")

        assert "AAPL News" in result
        assert "AAPL up 5%" in result
        assert "Reuters" in result
        assert "Strong earnings" in result
        assert "https://r.com/1" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_returns_no_news_message_when_empty(self, mock_retry, mock_ticker_cls):
        mock_retry.side_effect = lambda fn: []

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")
        assert result == "No news found for AAPL"

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_returns_no_news_message_when_none(self, mock_retry, mock_ticker_cls):
        mock_retry.side_effect = lambda fn: None

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")
        assert result == "No news found for AAPL"

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_filters_articles_outside_date_range(self, mock_retry, mock_ticker_cls):
        articles = [
            _nested_article(
                title="In range",
                pub_date="2024-01-15T10:00:00Z",
            ),
            _nested_article(
                title="Out of range",
                pub_date="2024-03-01T10:00:00Z",
            ),
        ]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")

        assert "In range" in result
        assert "Out of range" not in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_includes_articles_without_pub_date(self, mock_retry, mock_ticker_cls):
        """Articles without pub_date should not be filtered out."""
        articles = [_flat_article(title="Undated news")]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")

        assert "Undated news" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_all_articles_filtered_returns_no_news_in_range(
        self, mock_retry, mock_ticker_cls
    ):
        """When all articles have dates outside range, return 'no news' message."""
        articles = [
            _nested_article(title="Too early", pub_date="2023-06-01T10:00:00Z"),
            _nested_article(title="Too late", pub_date="2025-06-01T10:00:00Z"),
        ]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")

        assert "No news found for AAPL between 2024-01-01 and 2024-01-31" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_date_boundary_inclusive_start(self, mock_retry, mock_ticker_cls):
        """Article exactly on start_date should be included."""
        articles = [
            _nested_article(
                title="Start boundary",
                pub_date="2024-01-01T00:00:00Z",
            ),
        ]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")
        assert "Start boundary" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_date_boundary_inclusive_end(self, mock_retry, mock_ticker_cls):
        """Article exactly on end_date should be included."""
        articles = [
            _nested_article(
                title="End boundary",
                pub_date="2024-01-31T23:59:59Z",
            ),
        ]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")
        assert "End boundary" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_multiple_articles_all_included(self, mock_retry, mock_ticker_cls):
        articles = [
            _nested_article(title="News A", pub_date="2024-01-10T10:00:00Z"),
            _nested_article(title="News B", pub_date="2024-01-20T10:00:00Z"),
            _nested_article(title="News C", pub_date="2024-01-25T10:00:00Z"),
        ]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")
        assert "News A" in result
        assert "News B" in result
        assert "News C" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_article_without_summary_omits_summary_line(
        self, mock_retry, mock_ticker_cls
    ):
        articles = [
            _nested_article(title="No Summary", summary="", pub_date="2024-01-15T10:00:00Z"),
        ]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")
        assert "No Summary" in result
        # Summary line should not appear as extra content between title and link
        lines = result.strip().split("\n")
        title_line_idx = next(
            i for i, l in enumerate(lines) if "No Summary" in l
        )
        # Next non-empty line should be Link, not a summary
        remaining = [l for l in lines[title_line_idx + 1 :] if l.strip()]
        if remaining:
            assert remaining[0].startswith("Link:")

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_article_without_link_omits_link_line(self, mock_retry, mock_ticker_cls):
        articles = [
            _nested_article(title="No Link", url="", pub_date="2024-01-15T10:00:00Z"),
        ]
        # Need to clear the url from nested structure
        articles[0]["content"]["canonicalUrl"] = {"url": ""}
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")
        assert "No Link" in result
        assert "Link:" not in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_exception_returns_error_message(self, mock_retry, mock_ticker_cls):
        mock_retry.side_effect = RuntimeError("connection timeout")

        result = get_news_yfinance("AAPL", "2024-01-01", "2024-01-31")
        assert "Error fetching news for AAPL" in result
        assert "connection timeout" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_header_contains_ticker_and_dates(self, mock_retry, mock_ticker_cls):
        articles = [_flat_article(title="Test")]
        mock_retry.side_effect = lambda fn: articles

        result = get_news_yfinance("MSFT", "2024-03-01", "2024-03-31")
        assert "MSFT News" in result
        assert "2024-03-01" in result
        assert "2024-03-31" in result

    @patch("tradingagents.dataflows.yfinance_news.yf.Ticker")
    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_ticker_instantiated_with_symbol(self, mock_retry, mock_ticker_cls):
        mock_retry.side_effect = lambda fn: None

        get_news_yfinance("TSLA", "2024-01-01", "2024-01-31")
        mock_ticker_cls.assert_called_once_with("TSLA")


# ---------------------------------------------------------------------------
# get_global_news_yfinance
# ---------------------------------------------------------------------------

class TestGetGlobalNewsYfinance:
    """Tests for get_global_news_yfinance function."""

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_returns_formatted_global_news(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = [
            _nested_article(
                title="Markets rally",
                summary="Global optimism",
                publisher="AP",
                url="https://ap.com/1",
                pub_date="2024-01-14T10:00:00Z",
            ),
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")

        assert "Global Market News" in result
        assert "Markets rally" in result
        assert "AP" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_returns_no_news_message_when_empty(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = []
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")
        assert "No global news found for 2024-01-15" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_deduplicates_articles_by_title(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = [
            _nested_article(title="Duplicate News", pub_date="2024-01-14T10:00:00Z"),
            _nested_article(title="Duplicate News", pub_date="2024-01-14T11:00:00Z"),
            _nested_article(title="Unique News", pub_date="2024-01-14T12:00:00Z"),
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")

        assert result.count("Duplicate News") == 1
        assert "Unique News" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_limits_total_articles(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = [
            _nested_article(title=f"Article {i}", pub_date="2024-01-14T10:00:00Z")
            for i in range(20)
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15", limit=3)

        # Should only have 3 articles in output
        count = result.count("### Article")
        assert count == 3

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_uses_look_back_days_for_date_range(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = [
            _flat_article(title="Some news"),
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15", look_back_days=3)

        assert "2024-01-12" in result  # 15 - 3 = 12
        assert "2024-01-15" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_exception_returns_error_message(self, mock_retry):
        mock_retry.side_effect = ConnectionError("DNS failure")

        result = get_global_news_yfinance("2024-01-15")
        assert "Error fetching global news" in result
        assert "DNS failure" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_handles_flat_articles(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = [
            _flat_article(title="Flat news", publisher="NYT", link="https://nyt.com"),
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")

        assert "Flat news" in result
        assert "NYT" in result
        assert "https://nyt.com" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_skips_articles_published_after_curr_date(self, mock_retry):
        """Articles with pub_date after curr_date + 1 day should be skipped."""
        mock_search = MagicMock()
        mock_search.news = [
            _nested_article(title="Future article", pub_date="2025-06-01T10:00:00Z"),
            _nested_article(title="Past article", pub_date="2024-01-14T10:00:00Z"),
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")

        assert "Future article" not in result
        assert "Past article" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_stops_collecting_after_limit_reached(self, mock_retry):
        """Should stop querying once enough unique articles are collected."""
        call_count = 0

        def mock_retry_fn(fn):
            nonlocal call_count
            call_count += 1
            mock_search = MagicMock()
            mock_search.news = [
                _flat_article(title=f"Article from query {call_count}"),
            ]
            return mock_search

        mock_retry.side_effect = mock_retry_fn

        # limit=1 means we should stop after collecting 1 article
        result = get_global_news_yfinance("2024-01-15", limit=1)

        # First query gives 1 article which meets limit, should break
        assert call_count == 1

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_mixed_nested_and_flat_articles(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = [
            _nested_article(title="Nested one", pub_date="2024-01-14T10:00:00Z"),
            _flat_article(title="Flat one"),
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")

        assert "Nested one" in result
        assert "Flat one" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_default_look_back_is_7_days(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = [_flat_article(title="Default lookback")]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")

        assert "2024-01-08" in result  # 15 - 7 = 8

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_dedup_with_empty_title_skipped(self, mock_retry):
        """Articles with empty titles should be skipped in deduplication."""
        mock_search = MagicMock()
        mock_search.news = [
            _flat_article(title=""),
            _flat_article(title="Real news"),
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")

        # Empty title is falsy, so should be excluded from dedup
        assert "Real news" in result

    @patch("tradingagents.dataflows.yfinance_news.yf_retry")
    def test_nested_article_without_summary_omits_summary(self, mock_retry):
        mock_search = MagicMock()
        mock_search.news = [
            _nested_article(title="No summary", summary="", pub_date="2024-01-14T10:00:00Z"),
        ]
        mock_retry.return_value = mock_search

        result = get_global_news_yfinance("2024-01-15")
        lines = [l for l in result.split("\n") if l.strip()]
        title_idx = next(i for i, l in enumerate(lines) if "No summary" in l)
        # After the title line, next content line should be Link or nothing
        remaining = lines[title_idx + 1 :]
        for line in remaining:
            if line.strip():
                assert line.strip().startswith("Link:") or line.strip().startswith("##")
                break
