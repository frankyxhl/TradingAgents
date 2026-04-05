# tests/test_neutral_debator.py
"""
Tests for tradingagents/agents/risk_mgmt/neutral_debator.py

Covers create_neutral_debator() — a LangGraph node factory for the
neutral risk analyst in the risk debate sub-graph.  All LLM calls are
mocked; no real API traffic.
"""

from unittest.mock import MagicMock, patch

from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator

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


def _mock_llm(response_text="A balanced approach is best."):
    """Return a mock LLM whose .invoke() returns an object with .content."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=response_text)
    return llm


# ---------------------------------------------------------------------------
# Tests — English label (output_language=English)
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_english_label_prefix(mock_lang):
    """When output_language is English, the argument uses 'Neutral Analyst' prefix."""
    llm = _mock_llm("We should diversify holdings.")
    node = create_neutral_debator(llm)
    result = node(_make_state())

    argument = result["risk_debate_state"]["current_neutral_response"]
    assert argument.startswith("Neutral Analyst:")


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_english_latest_speaker(mock_lang):
    """latest_speaker is always 'Neutral' regardless of language."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)
    result = node(_make_state())

    assert result["risk_debate_state"]["latest_speaker"] == "Neutral"


# ---------------------------------------------------------------------------
# Tests — Chinese label (output_language=Chinese)
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value=" Write your entire response in Chinese.",
)
def test_chinese_label_prefix(mock_lang):
    """When output_language is Chinese, the argument uses '中性分析师' prefix."""
    llm = _mock_llm("建议保持均衡配置。")
    node = create_neutral_debator(llm)
    result = node(_make_state())

    argument = result["risk_debate_state"]["current_neutral_response"]
    assert argument.startswith("中性分析师:")


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value=" Write your entire response in Chinese.",
)
def test_chinese_latest_speaker_still_english(mock_lang):
    """latest_speaker stays 'Neutral' even in Chinese mode."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)
    result = node(_make_state())

    assert result["risk_debate_state"]["latest_speaker"] == "Neutral"


# ---------------------------------------------------------------------------
# Tests — return structure
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_returns_risk_debate_state_dict(mock_lang):
    """Node returns a dict with a single 'risk_debate_state' key."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)
    result = node(_make_state())

    assert "risk_debate_state" in result
    assert isinstance(result["risk_debate_state"], dict)
    assert len(result) == 1


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_count_incremented(mock_lang):
    """The debate round count is incremented by 1."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)

    state = _make_state()
    state["risk_debate_state"]["count"] = 7
    result = node(state)

    assert result["risk_debate_state"]["count"] == 8


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_history_appended(mock_lang):
    """The neutral argument is appended to both history and neutral_history."""
    llm = _mock_llm("Consider both sides carefully.")
    node = create_neutral_debator(llm)

    state = _make_state()
    state["risk_debate_state"]["history"] = "Previous debate."
    state["risk_debate_state"]["neutral_history"] = "Previous neutral."
    result = node(state)

    rds = result["risk_debate_state"]
    assert "Previous debate." in rds["history"]
    assert "Neutral Analyst: Consider both sides carefully." in rds["history"]
    assert "Previous neutral." in rds["neutral_history"]
    assert "Neutral Analyst: Consider both sides carefully." in rds["neutral_history"]


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_preserves_other_histories(mock_lang):
    """Aggressive and conservative histories are preserved unchanged."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)

    state = _make_state()
    state["risk_debate_state"]["aggressive_history"] = "aggressive notes"
    state["risk_debate_state"]["conservative_history"] = "conservative notes"
    result = node(state)

    rds = result["risk_debate_state"]
    assert rds["aggressive_history"] == "aggressive notes"
    assert rds["conservative_history"] == "conservative notes"


# ---------------------------------------------------------------------------
# Tests — LLM invocation
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_llm_invoked_once(mock_lang):
    """LLM.invoke() is called exactly once per node invocation."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)
    node(_make_state())

    assert llm.invoke.call_count == 1


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_prompt_contains_trader_decision(mock_lang):
    """The prompt sent to the LLM includes the trader's investment plan."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)
    node(_make_state(trader_investment_plan="short NVDA at 800"))

    prompt = llm.invoke.call_args[0][0]
    assert "short NVDA at 800" in prompt


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_prompt_contains_reports(mock_lang):
    """The prompt includes all four report types."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)
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
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_prompt_contains_debate_context(mock_lang):
    """The prompt includes the current aggressive and conservative responses."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)

    state = _make_state()
    state["risk_debate_state"]["current_aggressive_response"] = "AGGR-ARG"
    state["risk_debate_state"]["current_conservative_response"] = "CONS-ARG"
    state["risk_debate_state"]["history"] = "PREV-HISTORY"
    node(state)

    prompt = llm.invoke.call_args[0][0]
    assert "AGGR-ARG" in prompt
    assert "CONS-ARG" in prompt
    assert "PREV-HISTORY" in prompt


# ---------------------------------------------------------------------------
# Tests — state reading with missing optional keys
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_handles_minimal_risk_debate_state(mock_lang):
    """Node handles a risk_debate_state with only the required 'count' key."""
    llm = _mock_llm()
    node = create_neutral_debator(llm)

    minimal_state = _make_state(risk_debate_state={"count": 0})
    result = node(minimal_state)

    assert result["risk_debate_state"]["latest_speaker"] == "Neutral"
    assert result["risk_debate_state"]["count"] == 1


# ---------------------------------------------------------------------------
# Tests — current_neutral_response contains LLM output
# ---------------------------------------------------------------------------


@patch(
    "tradingagents.agents.risk_mgmt.neutral_debator.get_language_instruction",
    return_value="",
)
def test_response_contains_llm_content(mock_lang):
    """The current_neutral_response includes the LLM's actual output."""
    llm = _mock_llm("Diversification is key to managing risk.")
    node = create_neutral_debator(llm)
    result = node(_make_state())

    response = result["risk_debate_state"]["current_neutral_response"]
    assert "Diversification is key to managing risk." in response
