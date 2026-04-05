# tests/test_aggressive_debator.py
"""
Tests for tradingagents/agents/risk_mgmt/aggressive_debator.py

Covers create_aggressive_debator() — a LangGraph node factory for the
aggressive risk analyst in the risk debate sub-graph.  All LLM calls are
mocked; no real API traffic.
"""

from unittest.mock import MagicMock, patch

from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    risk_debate_state=None,
    market_report="market data",
    sentiment_report="sentiment data",
    news_report="news data",
    fundamentals_report="fundamentals data",
    trader_investment_plan="buy AAPL",
):
    """Build a minimal state dict matching the AgentState schema."""
    if risk_debate_state is None:
        risk_debate_state = {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "latest_speaker": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
        }
    return {
        "risk_debate_state": risk_debate_state,
        "market_report": market_report,
        "sentiment_report": sentiment_report,
        "news_report": news_report,
        "fundamentals_report": fundamentals_report,
        "trader_investment_plan": trader_investment_plan,
    }


def _mock_llm(response_text="I advocate for high-risk strategies."):
    """Return a mock LLM whose .invoke() returns an object with .content."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=response_text)
    return llm


# ---------------------------------------------------------------------------
# Tests — English label (output_language=English)
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_english_label_prefix(mock_lang):
    """When output_language is English, the argument uses 'Aggressive Analyst' prefix."""
    llm = _mock_llm("Go big or go home.")
    node = create_aggressive_debator(llm)
    result = node(_make_state())

    argument = result["risk_debate_state"]["current_aggressive_response"]
    assert argument.startswith("Aggressive Analyst:")


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_english_latest_speaker(mock_lang):
    """latest_speaker is always 'Aggressive' regardless of language."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)
    result = node(_make_state())

    assert result["risk_debate_state"]["latest_speaker"] == "Aggressive"


# ---------------------------------------------------------------------------
# Tests — Chinese label (output_language=Chinese)
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value=" Write your entire response in Chinese.",
)
def test_chinese_label_prefix(mock_lang):
    """When output_language is Chinese, the argument uses '激进分析师' prefix."""
    llm = _mock_llm("应该加大仓位。")
    node = create_aggressive_debator(llm)
    result = node(_make_state())

    argument = result["risk_debate_state"]["current_aggressive_response"]
    assert argument.startswith("激进分析师:")


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value=" Write your entire response in Chinese.",
)
def test_chinese_latest_speaker_still_english(mock_lang):
    """latest_speaker stays 'Aggressive' even in Chinese mode."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)
    result = node(_make_state())

    assert result["risk_debate_state"]["latest_speaker"] == "Aggressive"


# ---------------------------------------------------------------------------
# Tests — return structure
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_returns_risk_debate_state_dict(mock_lang):
    """Node returns a dict with a single 'risk_debate_state' key."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)
    result = node(_make_state())

    assert "risk_debate_state" in result
    assert isinstance(result["risk_debate_state"], dict)
    assert len(result) == 1  # only risk_debate_state


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_count_incremented(mock_lang):
    """The debate round count is incremented by 1."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)

    state = _make_state()
    state["risk_debate_state"]["count"] = 5
    result = node(state)

    assert result["risk_debate_state"]["count"] == 6


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_history_appended(mock_lang):
    """The aggressive argument is appended to both history and aggressive_history."""
    llm = _mock_llm("Strong upside potential.")
    node = create_aggressive_debator(llm)

    state = _make_state()
    state["risk_debate_state"]["history"] = "Previous debate."
    state["risk_debate_state"]["aggressive_history"] = "Previous aggressive."
    result = node(state)

    rds = result["risk_debate_state"]
    assert "Previous debate." in rds["history"]
    assert "Aggressive Analyst: Strong upside potential." in rds["history"]
    assert "Previous aggressive." in rds["aggressive_history"]
    assert "Aggressive Analyst: Strong upside potential." in rds["aggressive_history"]


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_preserves_other_histories(mock_lang):
    """Conservative and neutral histories are preserved unchanged."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)

    state = _make_state()
    state["risk_debate_state"]["conservative_history"] = "conservative notes"
    state["risk_debate_state"]["neutral_history"] = "neutral notes"
    result = node(state)

    rds = result["risk_debate_state"]
    assert rds["conservative_history"] == "conservative notes"
    assert rds["neutral_history"] == "neutral notes"


# ---------------------------------------------------------------------------
# Tests — LLM invocation
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_llm_invoked_once(mock_lang):
    """LLM.invoke() is called exactly once per node invocation."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)
    node(_make_state())

    assert llm.invoke.call_count == 1


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_prompt_contains_trader_decision(mock_lang):
    """The prompt sent to the LLM includes the trader's investment plan."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)
    node(_make_state(trader_investment_plan="sell TSLA at 200"))

    prompt = llm.invoke.call_args[0][0]
    assert "sell TSLA at 200" in prompt


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_prompt_contains_reports(mock_lang):
    """The prompt includes all four report types."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)
    node(
        _make_state(
            market_report="MKT-RPT",
            sentiment_report="SENT-RPT",
            news_report="NEWS-RPT",
            fundamentals_report="FUND-RPT",
        )
    )

    prompt = llm.invoke.call_args[0][0]
    assert "MKT-RPT" in prompt
    assert "SENT-RPT" in prompt
    assert "NEWS-RPT" in prompt
    assert "FUND-RPT" in prompt


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_prompt_contains_debate_context(mock_lang):
    """The prompt includes the current conservative and neutral responses."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)

    state = _make_state()
    state["risk_debate_state"]["current_conservative_response"] = "CONS-ARG"
    state["risk_debate_state"]["current_neutral_response"] = "NEUT-ARG"
    state["risk_debate_state"]["history"] = "PREV-HISTORY"
    node(state)

    prompt = llm.invoke.call_args[0][0]
    assert "CONS-ARG" in prompt
    assert "NEUT-ARG" in prompt
    assert "PREV-HISTORY" in prompt


# ---------------------------------------------------------------------------
# Tests — state reading with missing optional keys
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.aggressive_debator.get_language_instruction",
    return_value="",
)
def test_handles_minimal_risk_debate_state(mock_lang):
    """Node handles a risk_debate_state with only the required 'count' key."""
    llm = _mock_llm()
    node = create_aggressive_debator(llm)

    minimal_state = _make_state(risk_debate_state={"count": 0})
    result = node(minimal_state)

    # Should still produce a valid result without errors
    assert result["risk_debate_state"]["latest_speaker"] == "Aggressive"
    assert result["risk_debate_state"]["count"] == 1
