# tests/test_portfolio_manager.py
"""
Tests for tradingagents/agents/managers/portfolio_manager.py

Covers the create_portfolio_manager factory and the inner portfolio_manager_node,
including CN/EN prompt selection, rating scale handling, state update format,
LLM invocation, and risk debate context.
"""

from unittest.mock import MagicMock, patch

from tradingagents.agents.managers.portfolio_manager import create_portfolio_manager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    company_of_interest="AAPL",
    market_report="market report",
    sentiment_report="sentiment report",
    news_report="news report",
    fundamentals_report="fundamentals report",
    investment_plan="proposed trader plan",
    history="",
    aggressive_history="",
    conservative_history="",
    neutral_history="",
    current_aggressive_response="",
    current_conservative_response="",
    current_neutral_response="",
    count=0,
):
    """Build a minimal state dict matching what portfolio_manager_node expects."""
    return {
        "company_of_interest": company_of_interest,
        "market_report": market_report,
        "sentiment_report": sentiment_report,
        "news_report": news_report,
        "fundamentals_report": fundamentals_report,
        "investment_plan": investment_plan,
        "risk_debate_state": {
            "history": history,
            "aggressive_history": aggressive_history,
            "conservative_history": conservative_history,
            "neutral_history": neutral_history,
            "current_aggressive_response": current_aggressive_response,
            "current_conservative_response": current_conservative_response,
            "current_neutral_response": current_neutral_response,
            "count": count,
        },
    }


def _mock_llm(response_content="Buy with strong conviction."):
    """Create a mock LLM that returns a fixed response."""
    llm = MagicMock()
    response = MagicMock()
    response.content = response_content
    llm.invoke.return_value = response
    return llm


def _mock_memory(memories=None):
    """Create a mock memory object."""
    mem = MagicMock()
    if memories is None:
        memories = []
    mem.get_memories.return_value = memories
    return mem


# ---------------------------------------------------------------------------
# CN/EN prompt selection
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_chinese_prompt_when_language_instruction_non_empty(mock_lang):
    """When get_language_instruction returns non-empty (Chinese mode),
    the prompt should be in Chinese."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "投资组合经理" in prompt
    assert "风控分析师" in prompt


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_english_prompt_when_language_instruction_empty(mock_lang):
    """When get_language_instruction returns empty (English mode),
    the prompt should be in English."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Portfolio Manager" in prompt
    assert "risk analysts" in prompt.lower()


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_chinese_prompt_includes_lang_instruction_suffix(mock_lang):
    """The Chinese prompt should include the language instruction at the end."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Write your entire response in Chinese." in prompt


# ---------------------------------------------------------------------------
# Rating scale handling
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_chinese_rating_scale_terms(mock_lang):
    """Chinese prompt should include the five Chinese rating terms."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    for term in ["买入", "增持", "持有", "减持", "卖出"]:
        assert term in prompt


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_english_rating_scale_terms(mock_lang):
    """English prompt should include the five English rating terms."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    for term in ["Buy", "Overweight", "Hold", "Underweight", "Sell"]:
        assert term in prompt


# ---------------------------------------------------------------------------
# State update format
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_returns_correct_top_level_keys(mock_lang):
    """Returned dict must contain 'risk_debate_state' and 'final_trade_decision'."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(_make_state())

    assert set(result.keys()) == {"risk_debate_state", "final_trade_decision"}


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_risk_debate_state_has_required_keys(mock_lang):
    """The risk_debate_state must contain all required keys."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(_make_state())

    debate_state = result["risk_debate_state"]
    expected_keys = {
        "judge_decision",
        "history",
        "aggressive_history",
        "conservative_history",
        "neutral_history",
        "latest_speaker",
        "current_aggressive_response",
        "current_conservative_response",
        "current_neutral_response",
        "count",
    }
    assert set(debate_state.keys()) == expected_keys


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_judge_decision_set_to_llm_response(mock_lang):
    """judge_decision should be set to the LLM response content."""
    mock_lang.return_value = ""
    llm = _mock_llm("Underweight - reduce exposure")
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(_make_state())

    assert result["risk_debate_state"]["judge_decision"] == "Underweight - reduce exposure"


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_final_trade_decision_set_to_llm_response(mock_lang):
    """final_trade_decision should be set to the LLM response content."""
    mock_lang.return_value = ""
    llm = _mock_llm("Buy with 40% position")
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(_make_state())

    assert result["final_trade_decision"] == "Buy with 40% position"


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_latest_speaker_is_judge(mock_lang):
    """latest_speaker should always be set to 'Judge'."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(_make_state())

    assert result["risk_debate_state"]["latest_speaker"] == "Judge"


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_count_preserved_from_input_state(mock_lang):
    """The count should be passed through unchanged."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(_make_state(count=7))

    assert result["risk_debate_state"]["count"] == 7


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_history_preserved_from_input_state(mock_lang):
    """history should be passed through unchanged."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(_make_state(history="risk debate round 1"))

    assert result["risk_debate_state"]["history"] == "risk debate round 1"


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_sub_histories_preserved(mock_lang):
    """aggressive, conservative, and neutral histories should be passed through."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(
        _make_state(
            aggressive_history="aggressive says go big",
            conservative_history="conservative says careful",
            neutral_history="neutral says balanced",
        )
    )

    ds = result["risk_debate_state"]
    assert ds["aggressive_history"] == "aggressive says go big"
    assert ds["conservative_history"] == "conservative says careful"
    assert ds["neutral_history"] == "neutral says balanced"


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_current_responses_preserved(mock_lang):
    """current_*_response fields should be passed through unchanged."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    result = node(
        _make_state(
            current_aggressive_response="agg resp",
            current_conservative_response="con resp",
            current_neutral_response="neu resp",
        )
    )

    ds = result["risk_debate_state"]
    assert ds["current_aggressive_response"] == "agg resp"
    assert ds["current_conservative_response"] == "con resp"
    assert ds["current_neutral_response"] == "neu resp"


# ---------------------------------------------------------------------------
# LLM invocation with risk debate context
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_llm_invoke_called_once(mock_lang):
    """llm.invoke should be called exactly once."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state())

    llm.invoke.assert_called_once()


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_prompt_contains_risk_debate_history(mock_lang):
    """The prompt should include the risk debate history from state."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state(history="Aggressive: go all in. Conservative: wait."))

    prompt = llm.invoke.call_args[0][0]
    assert "Aggressive: go all in. Conservative: wait." in prompt


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_prompt_contains_trader_plan(mock_lang):
    """The prompt should include the trader's proposed investment plan."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state(investment_plan="Buy AAPL at $150 with stop at $140"))

    prompt = llm.invoke.call_args[0][0]
    assert "Buy AAPL at $150 with stop at $140" in prompt


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_prompt_contains_instrument_context(mock_lang):
    """The prompt should include the instrument context with the ticker."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state(company_of_interest="MSFT"))

    prompt = llm.invoke.call_args[0][0]
    assert "MSFT" in prompt


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_chinese_prompt_contains_trader_plan(mock_lang):
    """In Chinese mode, the prompt should still include the trader's plan."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state(investment_plan="Buy BABA at $100"))

    prompt = llm.invoke.call_args[0][0]
    assert "Buy BABA at $100" in prompt


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_chinese_prompt_contains_debate_history(mock_lang):
    """In Chinese mode, the prompt should still include the debate history."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state(history="Risk debate content here"))

    prompt = llm.invoke.call_args[0][0]
    assert "Risk debate content here" in prompt


# ---------------------------------------------------------------------------
# Memory integration
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_memory_get_memories_called(mock_lang):
    """memory.get_memories should be called with n_matches=2."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(_make_state())

    memory.get_memories.assert_called_once()
    call_kwargs = memory.get_memories.call_args[1]
    assert call_kwargs.get("n_matches") == 2


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_memory_situation_includes_reports(mock_lang):
    """The situation string passed to memory should include all four reports."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_portfolio_manager(llm, memory)
    node(
        _make_state(
            market_report="MR_X",
            sentiment_report="SR_X",
            news_report="NR_X",
            fundamentals_report="FR_X",
        )
    )

    situation_arg = memory.get_memories.call_args[0][0]
    assert "MR_X" in situation_arg
    assert "SR_X" in situation_arg
    assert "NR_X" in situation_arg
    assert "FR_X" in situation_arg


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_past_memories_included_in_prompt(mock_lang):
    """When memories exist, their recommendations appear in the prompt."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memories = [
        {"recommendation": "Lesson: always set stop losses."},
        {"recommendation": "Lesson: diversify across sectors."},
    ]
    memory = _mock_memory(memories)

    node = create_portfolio_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Lesson: always set stop losses." in prompt
    assert "Lesson: diversify across sectors." in prompt


@patch("tradingagents.agents.managers.portfolio_manager.get_language_instruction")
def test_empty_memories_no_error(mock_lang):
    """When no memories exist, the function should still work."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory([])

    node = create_portfolio_manager(llm, memory)
    result = node(_make_state())

    assert "risk_debate_state" in result
    assert "final_trade_decision" in result


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def test_create_portfolio_manager_returns_callable():
    """create_portfolio_manager should return a callable."""
    llm = _mock_llm()
    memory = _mock_memory()

    result = create_portfolio_manager(llm, memory)
    assert callable(result)
