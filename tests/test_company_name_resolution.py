"""Tests for LVM-2004: company name resolution from ticker."""

import logging
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_name_cache():
    """Clear Propagator company name cache before each test."""
    from tradingagents.graph.propagation import Propagator

    Propagator._company_name_cache.clear()
    yield
    Propagator._company_name_cache.clear()


# ---------------------------------------------------------------------------
# create_initial_state — resolved_company_name
# ---------------------------------------------------------------------------


def test_create_initial_state_contains_resolved_company_name():
    """yfinance longName should populate resolved_company_name."""
    mock_ticker = MagicMock()
    mock_ticker.info = {"longName": "ispace, inc."}

    with patch("yfinance.Ticker", return_value=mock_ticker):
        from tradingagents.graph.propagation import Propagator

        p = Propagator()
        state = p.create_initial_state("9348.T", "2026-04-04")

    assert state["resolved_company_name"] == "ispace, inc."


def test_create_initial_state_fallback_on_yfinance_failure():
    """When yfinance raises, resolved_company_name should fall back to ticker."""
    with patch("yfinance.Ticker", side_effect=Exception("network error")):
        from tradingagents.graph.propagation import Propagator

        p = Propagator()
        state = p.create_initial_state("9348.T", "2026-04-04")

    assert state["resolved_company_name"] == "9348.T"


def test_create_initial_state_fallback_logs_warning(caplog):
    """When yfinance raises, a warning should be logged."""
    with patch("yfinance.Ticker", side_effect=Exception("network error")):
        from tradingagents.graph.propagation import Propagator

        p = Propagator()
        with caplog.at_level(logging.WARNING):
            p.create_initial_state("9348.T", "2026-04-04")

    assert any("Failed to resolve company name" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# build_instrument_context — company_name parameter
# ---------------------------------------------------------------------------


def test_build_instrument_context_with_company_name():
    """With company_name, output should contain both name and ticker."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("9348.T", "ispace, inc.")
    assert "ispace" in result
    assert "9348.T" in result


def test_build_instrument_context_without_company_name():
    """Without company_name, output should still contain ticker and not error."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("9348.T")
    assert "9348.T" in result


def test_build_instrument_context_no_duplication_when_name_equals_ticker():
    """When company_name equals ticker (fallback), should not show 'AAPL (AAPL)'."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("9348.T", "9348.T")
    assert "9348.T" in result
    assert "9348.T (9348.T)" not in result


def test_build_instrument_context_backward_compatible():
    """Existing single-arg usage must still work (company_name defaults to None)."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("AAPL")
    assert isinstance(result, str)
    assert "AAPL" in result
    # Should mention exchange suffix guidance
    assert "exchange suffix" in result.lower() or "exchange" in result.lower()
