# tests/test_conditional_logic.py
"""
Tests for tradingagents/graph/conditional_logic.py

Covers all conditional edge functions used by LangGraph, with explicit
attention to Chinese-label routing (看多分析师 / 看空分析师) — the class of
bug that bit the livermore fork on 2026-04-04.
"""

from unittest.mock import MagicMock

import pytest

from tradingagents.graph.conditional_logic import ConditionalLogic

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(messages=None, investment_debate_state=None, risk_debate_state=None):
    """Build a minimal AgentState-like dict for testing."""
    state = {}
    if messages is not None:
        state["messages"] = messages
    if investment_debate_state is not None:
        state["investment_debate_state"] = investment_debate_state
    if risk_debate_state is not None:
        state["risk_debate_state"] = risk_debate_state
    return state


def _msg(tool_calls=None):
    """Create a mock message with optional tool_calls."""
    m = MagicMock()
    m.tool_calls = tool_calls  # None = falsy, list = truthy
    return m


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def logic():
    """ConditionalLogic with default 1-round limits."""
    return ConditionalLogic(max_debate_rounds=1, max_risk_discuss_rounds=1)


@pytest.fixture
def logic_multi():
    """ConditionalLogic with 3-round limits for round-limit boundary tests."""
    return ConditionalLogic(max_debate_rounds=3, max_risk_discuss_rounds=3)


# ---------------------------------------------------------------------------
# should_continue_market
# ---------------------------------------------------------------------------


def test_market_routes_to_tools_when_tool_calls_present(logic):
    state = _make_state(messages=[_msg(tool_calls=[MagicMock()])])
    assert logic.should_continue_market(state) == "tools_market"


def test_market_routes_to_clear_when_no_tool_calls(logic):
    state = _make_state(messages=[_msg(tool_calls=None)])
    assert logic.should_continue_market(state) == "Msg Clear Market"


def test_market_routes_to_clear_when_tool_calls_empty_list(logic):
    """Empty list tool_calls (some LLM providers) must also route to clear."""
    state = _make_state(messages=[_msg(tool_calls=[])])
    assert logic.should_continue_market(state) == "Msg Clear Market"


def test_market_uses_last_message_only(logic):
    # First message has tool calls; last one does not — must return "Msg Clear Market"
    state = _make_state(messages=[_msg(tool_calls=[MagicMock()]), _msg(tool_calls=None)])
    assert logic.should_continue_market(state) == "Msg Clear Market"


# ---------------------------------------------------------------------------
# should_continue_social
# ---------------------------------------------------------------------------


def test_social_routes_to_tools_when_tool_calls_present(logic):
    state = _make_state(messages=[_msg(tool_calls=[MagicMock()])])
    assert logic.should_continue_social(state) == "tools_social"


def test_social_routes_to_clear_when_no_tool_calls(logic):
    state = _make_state(messages=[_msg(tool_calls=None)])
    assert logic.should_continue_social(state) == "Msg Clear Social"


# ---------------------------------------------------------------------------
# should_continue_news
# ---------------------------------------------------------------------------


def test_news_routes_to_tools_when_tool_calls_present(logic):
    state = _make_state(messages=[_msg(tool_calls=[MagicMock()])])
    assert logic.should_continue_news(state) == "tools_news"


def test_news_routes_to_clear_when_no_tool_calls(logic):
    state = _make_state(messages=[_msg(tool_calls=None)])
    assert logic.should_continue_news(state) == "Msg Clear News"


# ---------------------------------------------------------------------------
# should_continue_fundamentals
# ---------------------------------------------------------------------------


def test_fundamentals_routes_to_tools_when_tool_calls_present(logic):
    state = _make_state(messages=[_msg(tool_calls=[MagicMock()])])
    assert logic.should_continue_fundamentals(state) == "tools_fundamentals"


def test_fundamentals_routes_to_clear_when_no_tool_calls(logic):
    state = _make_state(messages=[_msg(tool_calls=None)])
    assert logic.should_continue_fundamentals(state) == "Msg Clear Fundamentals"


# ---------------------------------------------------------------------------
# should_continue_debate — English labels
# ---------------------------------------------------------------------------


def _debate_state(current_response, count=0):
    return {"current_response": current_response, "count": count}


def test_debate_english_bull_routes_to_bear(logic):
    """'Bull Researcher' prefix must route to Bear Researcher."""
    state = _make_state(
        investment_debate_state=_debate_state("Bull Researcher: I think we should buy.")
    )
    assert logic.should_continue_debate(state) == "Bear Researcher"


def test_debate_english_bull_prefix_only_routes_to_bear(logic):
    """Any string starting with 'Bull' routes to Bear Researcher."""
    state = _make_state(investment_debate_state=_debate_state("Bull: strong momentum"))
    assert logic.should_continue_debate(state) == "Bear Researcher"


def test_debate_english_bear_routes_to_bull(logic):
    """'Bear Researcher' prefix must route to Bull Researcher (default branch)."""
    state = _make_state(
        investment_debate_state=_debate_state("Bear Researcher: risks are too high.")
    )
    assert logic.should_continue_debate(state) == "Bull Researcher"


def test_debate_english_neutral_routes_to_bull(logic):
    """Unrecognised prefix falls through to Bull Researcher."""
    state = _make_state(investment_debate_state=_debate_state("Neutral comment"))
    assert logic.should_continue_debate(state) == "Bull Researcher"


# ---------------------------------------------------------------------------
# should_continue_debate — Chinese labels (livermore fork regression)
# ---------------------------------------------------------------------------


def test_debate_chinese_bull_label_routes_to_bear(logic):
    """看多 prefix must route to Bear Researcher — the 2026-04-04 regression case."""
    state = _make_state(investment_debate_state=_debate_state("看多分析师：建议买入。"))
    assert logic.should_continue_debate(state) == "Bear Researcher"


def test_debate_chinese_bull_prefix_bare_routes_to_bear(logic):
    """Bare 看多 prefix still routes to Bear Researcher."""
    state = _make_state(investment_debate_state=_debate_state("看多：市场强势"))
    assert logic.should_continue_debate(state) == "Bear Researcher"


def test_debate_chinese_bear_label_routes_to_bull(logic):
    """看空 prefix (not 看多) must fall through to Bull Researcher."""
    state = _make_state(investment_debate_state=_debate_state("看空分析师：风险过高。"))
    assert logic.should_continue_debate(state) == "Bull Researcher"


# ---------------------------------------------------------------------------
# should_continue_debate — round limit
# ---------------------------------------------------------------------------


def test_debate_round_limit_reached_routes_to_research_manager(logic):
    """When count >= 2 * max_debate_rounds the debate ends."""
    # max_debate_rounds=1 → threshold is 2
    state = _make_state(investment_debate_state=_debate_state("Bull Researcher", count=2))
    assert logic.should_continue_debate(state) == "Research Manager"


def test_debate_round_limit_exactly_at_threshold(logic):
    state = _make_state(investment_debate_state=_debate_state("看多分析师", count=2))
    assert logic.should_continue_debate(state) == "Research Manager"


def test_debate_round_limit_one_below_threshold_continues(logic):
    """count=1 is below threshold 2 → should NOT go to Research Manager."""
    state = _make_state(investment_debate_state=_debate_state("Bull Researcher", count=1))
    assert logic.should_continue_debate(state) != "Research Manager"


def test_debate_multi_round_limit(logic_multi):
    """With max_debate_rounds=3, threshold is 6."""
    # count=5 → still debating
    state = _make_state(investment_debate_state=_debate_state("Bear Researcher", count=5))
    assert logic_multi.should_continue_debate(state) != "Research Manager"
    # count=6 → done
    state = _make_state(investment_debate_state=_debate_state("Bear Researcher", count=6))
    assert logic_multi.should_continue_debate(state) == "Research Manager"


def test_debate_count_above_threshold_also_routes_to_research_manager(logic):
    """count well above threshold still terminates correctly."""
    state = _make_state(investment_debate_state=_debate_state("Bull Researcher", count=100))
    assert logic.should_continue_debate(state) == "Research Manager"


# ---------------------------------------------------------------------------
# should_continue_risk_analysis — English labels
# ---------------------------------------------------------------------------


def _risk_state(latest_speaker, count=0):
    return {"latest_speaker": latest_speaker, "count": count}


def test_risk_english_aggressive_routes_to_conservative(logic):
    state = _make_state(risk_debate_state=_risk_state("Aggressive Analyst"))
    assert logic.should_continue_risk_analysis(state) == "Conservative Analyst"


def test_risk_english_aggressive_prefix_routes_to_conservative(logic):
    state = _make_state(risk_debate_state=_risk_state("Aggressive: go big"))
    assert logic.should_continue_risk_analysis(state) == "Conservative Analyst"


def test_risk_english_conservative_routes_to_neutral(logic):
    state = _make_state(risk_debate_state=_risk_state("Conservative Analyst"))
    assert logic.should_continue_risk_analysis(state) == "Neutral Analyst"


def test_risk_english_conservative_prefix_routes_to_neutral(logic):
    state = _make_state(risk_debate_state=_risk_state("Conservative: be cautious"))
    assert logic.should_continue_risk_analysis(state) == "Neutral Analyst"


def test_risk_english_neutral_routes_to_aggressive(logic):
    """Neutral (and any other unrecognised label) falls through to Aggressive Analyst."""
    state = _make_state(risk_debate_state=_risk_state("Neutral Analyst"))
    assert logic.should_continue_risk_analysis(state) == "Aggressive Analyst"


def test_risk_english_unknown_speaker_routes_to_aggressive(logic):
    state = _make_state(risk_debate_state=_risk_state("Portfolio Manager"))
    assert logic.should_continue_risk_analysis(state) == "Aggressive Analyst"


# ---------------------------------------------------------------------------
# should_continue_risk_analysis — Chinese labels
# ---------------------------------------------------------------------------


def test_risk_chinese_aggressive_routes_to_conservative(logic):
    """激进 prefix must route to Conservative Analyst."""
    state = _make_state(risk_debate_state=_risk_state("激进分析师：应该加仓"))
    assert logic.should_continue_risk_analysis(state) == "Conservative Analyst"


def test_risk_chinese_aggressive_bare_prefix_routes_to_conservative(logic):
    state = _make_state(risk_debate_state=_risk_state("激进：建议买入"))
    assert logic.should_continue_risk_analysis(state) == "Conservative Analyst"


def test_risk_chinese_conservative_routes_to_neutral(logic):
    """保守 prefix must route to Neutral Analyst."""
    state = _make_state(risk_debate_state=_risk_state("保守分析师：风险过高"))
    assert logic.should_continue_risk_analysis(state) == "Neutral Analyst"


def test_risk_chinese_conservative_bare_prefix_routes_to_neutral(logic):
    state = _make_state(risk_debate_state=_risk_state("保守：减少仓位"))
    assert logic.should_continue_risk_analysis(state) == "Neutral Analyst"


def test_risk_chinese_neutral_speaker_routes_to_aggressive(logic):
    """中性 is not a recognised prefix — falls through to Aggressive Analyst."""
    state = _make_state(risk_debate_state=_risk_state("中性分析师：保持观望"))
    assert logic.should_continue_risk_analysis(state) == "Aggressive Analyst"


# ---------------------------------------------------------------------------
# should_continue_risk_analysis — round limit
# ---------------------------------------------------------------------------


def test_risk_round_limit_reached_routes_to_portfolio_manager(logic):
    """When count >= 3 * max_risk_discuss_rounds the risk debate ends."""
    # max_risk_discuss_rounds=1 → threshold is 3
    state = _make_state(risk_debate_state=_risk_state("Aggressive Analyst", count=3))
    assert logic.should_continue_risk_analysis(state) == "Portfolio Manager"


def test_risk_round_limit_exactly_at_threshold(logic):
    state = _make_state(risk_debate_state=_risk_state("激进分析师", count=3))
    assert logic.should_continue_risk_analysis(state) == "Portfolio Manager"


def test_risk_round_limit_one_below_threshold_continues(logic):
    state = _make_state(risk_debate_state=_risk_state("Aggressive Analyst", count=2))
    assert logic.should_continue_risk_analysis(state) != "Portfolio Manager"


def test_risk_multi_round_limit(logic_multi):
    """With max_risk_discuss_rounds=3, threshold is 9."""
    state = _make_state(risk_debate_state=_risk_state("Conservative Analyst", count=8))
    assert logic_multi.should_continue_risk_analysis(state) != "Portfolio Manager"

    state = _make_state(risk_debate_state=_risk_state("Conservative Analyst", count=9))
    assert logic_multi.should_continue_risk_analysis(state) == "Portfolio Manager"


def test_risk_count_above_threshold_routes_to_portfolio_manager(logic):
    state = _make_state(risk_debate_state=_risk_state("Neutral Analyst", count=999))
    assert logic.should_continue_risk_analysis(state) == "Portfolio Manager"


# ---------------------------------------------------------------------------
# ConditionalLogic constructor — parameter storage
# ---------------------------------------------------------------------------


def test_constructor_stores_debate_rounds():
    cl = ConditionalLogic(max_debate_rounds=5, max_risk_discuss_rounds=2)
    assert cl.max_debate_rounds == 5


def test_constructor_stores_risk_rounds():
    cl = ConditionalLogic(max_debate_rounds=5, max_risk_discuss_rounds=2)
    assert cl.max_risk_discuss_rounds == 2


def test_constructor_defaults():
    cl = ConditionalLogic()
    assert cl.max_debate_rounds == 1
    assert cl.max_risk_discuss_rounds == 1
