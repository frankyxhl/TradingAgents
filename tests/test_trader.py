# tests/test_trader.py
"""
Tests for tradingagents/agents/trader/trader.py

Covers the create_trader factory and the inner trader_node function,
including CN/EN prompt selection, state update format, memory integration,
LLM invocation, and sender metadata.
"""

from unittest.mock import MagicMock, patch

from tradingagents.agents.trader.trader import create_trader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    company_of_interest="AAPL",
    investment_plan="Buy AAPL at $150",
    market_report="market report",
    sentiment_report="sentiment report",
    news_report="news report",
    fundamentals_report="fundamentals report",
):
    """Build a minimal state dict matching what trader_node expects."""
    return {
        "company_of_interest": company_of_interest,
        "investment_plan": investment_plan,
        "market_report": market_report,
        "sentiment_report": sentiment_report,
        "news_report": news_report,
        "fundamentals_report": fundamentals_report,
    }


def _mock_llm(response_content="FINAL TRANSACTION PROPOSAL: **BUY**"):
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


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_chinese_prompt_when_language_instruction_non_empty(mock_lang):
    """When get_language_instruction returns a non-empty string (Chinese mode),
    the system prompt should contain Chinese text."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "你是一名交易员" in system_content
    assert "最终交易建议" in system_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_chinese_user_prompt_when_language_instruction_non_empty(mock_lang):
    """When in Chinese mode, the user prompt should be in Chinese."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state(company_of_interest="TSLA"))

    messages = llm.invoke.call_args[0][0]
    user_content = messages[1]["content"]
    assert "基于分析师团队的综合分析" in user_content
    assert "TSLA" in user_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_english_prompt_when_language_instruction_empty(mock_lang):
    """When get_language_instruction returns empty string (English mode),
    the system prompt should contain English text."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "You are a trading agent" in system_content
    assert "FINAL TRANSACTION PROPOSAL" in system_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_english_user_prompt_when_language_instruction_empty(mock_lang):
    """When in English mode, the user prompt should be in English."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state(company_of_interest="MSFT"))

    messages = llm.invoke.call_args[0][0]
    user_content = messages[1]["content"]
    assert "comprehensive analysis by a team of analysts" in user_content
    assert "MSFT" in user_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_language_instruction_appended_to_chinese_system_prompt(mock_lang):
    """In Chinese mode, the language instruction should appear in the system prompt."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "Write your entire response in Chinese." in system_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_no_language_instruction_in_english_system_prompt(mock_lang):
    """In English mode, no language instruction should appear."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "Write your entire response in" not in system_content


# ---------------------------------------------------------------------------
# State update format
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_returns_required_keys(mock_lang):
    """The returned dict must have messages, trader_investment_plan, and sender."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    result = trader(_make_state())

    assert set(result.keys()) == {"messages", "trader_investment_plan", "sender"}


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_messages_contains_llm_result(mock_lang):
    """messages should be a list containing the LLM response object."""
    mock_lang.return_value = ""
    llm = _mock_llm("BUY recommendation")
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    result = trader(_make_state())

    assert len(result["messages"]) == 1
    assert result["messages"][0] == llm.invoke.return_value


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_trader_investment_plan_is_llm_content(mock_lang):
    """trader_investment_plan should be the content of the LLM response."""
    mock_lang.return_value = ""
    llm = _mock_llm("BUY at $150 with stop loss at $140")
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    result = trader(_make_state())

    assert result["trader_investment_plan"] == "BUY at $150 with stop loss at $140"


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_sender_is_trader(mock_lang):
    """The sender key should be 'Trader'."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    result = trader(_make_state())

    assert result["sender"] == "Trader"


# ---------------------------------------------------------------------------
# Conclusion format in prompt
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_english_conclusion_format_in_system_prompt(mock_lang):
    """English mode should instruct LLM to end with FINAL TRANSACTION PROPOSAL."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**" in system_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_chinese_conclusion_format_in_system_prompt(mock_lang):
    """Chinese mode should instruct LLM to end with the Chinese conclusion format."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "最终交易建议：**买入/持有/卖出**" in system_content


# ---------------------------------------------------------------------------
# LLM invocation
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_llm_invoke_called_once(mock_lang):
    """llm.invoke should be called exactly once per trader call."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    llm.invoke.assert_called_once()


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_llm_receives_system_and_user_messages(mock_lang):
    """The LLM should receive a list with system and user messages."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_user_prompt_contains_investment_plan(mock_lang):
    """The user prompt should include the investment plan from state."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state(investment_plan="Accumulate NVDA below $800"))

    messages = llm.invoke.call_args[0][0]
    user_content = messages[1]["content"]
    assert "Accumulate NVDA below $800" in user_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_user_prompt_contains_instrument_context(mock_lang):
    """The user prompt should include instrument context for the ticker."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state(company_of_interest="TSE:7203.T"))

    messages = llm.invoke.call_args[0][0]
    user_content = messages[1]["content"]
    assert "TSE:7203.T" in user_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_system_prompt_contains_trading_role(mock_lang):
    """The system prompt should describe the trading agent role."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "buy" in system_content.lower()
    assert "sell" in system_content.lower()
    assert "hold" in system_content.lower()


# ---------------------------------------------------------------------------
# State reads: reports feed into LLM context
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_all_reports_feed_into_memory_lookup(mock_lang):
    """All four reports should be combined for the memory lookup."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(
        _make_state(
            market_report="MR_UNIQUE",
            sentiment_report="SR_UNIQUE",
            news_report="NR_UNIQUE",
            fundamentals_report="FR_UNIQUE",
        )
    )

    memory.get_memories.assert_called_once()
    situation_arg = memory.get_memories.call_args[0][0]
    assert "MR_UNIQUE" in situation_arg
    assert "SR_UNIQUE" in situation_arg
    assert "NR_UNIQUE" in situation_arg
    assert "FR_UNIQUE" in situation_arg


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_company_of_interest_in_user_prompt(mock_lang):
    """The company name from state should appear in the user prompt."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state(company_of_interest="GOOG"))

    messages = llm.invoke.call_args[0][0]
    user_content = messages[1]["content"]
    assert "GOOG" in user_content


# ---------------------------------------------------------------------------
# Memory integration
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_memory_get_memories_called_with_n_matches_2(mock_lang):
    """memory.get_memories should request n_matches=2."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state())

    memory.get_memories.assert_called_once_with(
        memory.get_memories.call_args[0][0],
        n_matches=2,
    )


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_past_memories_included_in_system_prompt(mock_lang):
    """When memories exist, their recommendations should appear in the system prompt."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memories = [
        {"recommendation": "Buying dips on AAPL worked last quarter."},
        {"recommendation": "Holding through volatility paid off."},
    ]
    memory = _mock_memory(memories)

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "Buying dips on AAPL worked last quarter." in system_content
    assert "Holding through volatility paid off." in system_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_no_memories_uses_fallback_text(mock_lang):
    """When no memories exist, fallback text should appear in system prompt."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory([])

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "No past memories found." in system_content


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_none_memories_uses_fallback_text(mock_lang):
    """When memory returns None, fallback text should appear."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = MagicMock()
    memory.get_memories.return_value = None

    trader = create_trader(llm, memory)
    trader(_make_state())

    messages = llm.invoke.call_args[0][0]
    system_content = messages[0]["content"]
    assert "No past memories found." in system_content


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def test_create_trader_returns_callable():
    """create_trader should return a callable."""
    llm = _mock_llm()
    memory = _mock_memory()

    result = create_trader(llm, memory)
    assert callable(result)


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_create_trader_binds_name_trader(mock_lang):
    """The partial function should bind name='Trader' so sender is 'Trader'."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    result = trader(_make_state())

    assert result["sender"] == "Trader"


# ---------------------------------------------------------------------------
# Chinese mode user prompt includes investment plan
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.trader.trader.get_language_instruction")
def test_chinese_user_prompt_includes_investment_plan(mock_lang):
    """In Chinese mode, the user prompt should still include the investment plan."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    trader = create_trader(llm, memory)
    trader(_make_state(investment_plan="Buy BABA at 80"))

    messages = llm.invoke.call_args[0][0]
    user_content = messages[1]["content"]
    assert "Buy BABA at 80" in user_content
    assert "投资计划" in user_content
