# tests/test_bull_researcher.py
"""
Tests for tradingagents/agents/researchers/bull_researcher.py

Covers the create_bull_researcher factory and the inner bull_node function,
including CN/EN label selection, state update format, memory integration,
and LLM invocation.
"""

from unittest.mock import MagicMock, patch

from tradingagents.agents.researchers.bull_researcher import create_bull_researcher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    market_report="market report",
    sentiment_report="sentiment report",
    news_report="news report",
    fundamentals_report="fundamentals report",
    history="",
    bull_history="",
    bear_history="",
    current_response="",
    count=0,
):
    """Build a minimal state dict matching what bull_node expects."""
    return {
        "market_report": market_report,
        "sentiment_report": sentiment_report,
        "news_report": news_report,
        "fundamentals_report": fundamentals_report,
        "investment_debate_state": {
            "history": history,
            "bull_history": bull_history,
            "bear_history": bear_history,
            "current_response": current_response,
            "count": count,
        },
    }


def _mock_llm(response_content="This stock has great potential."):
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
# CN/EN label prefix
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_label_chinese_when_language_instruction_non_empty(mock_lang):
    """When get_language_instruction returns a non-empty string (Chinese mode),
    the label should be '看多分析师'."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm("bullish argument")
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state())

    current_response = result["investment_debate_state"]["current_response"]
    assert current_response.startswith("看多分析师:")


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_label_english_when_language_instruction_empty(mock_lang):
    """When get_language_instruction returns empty string (English mode),
    the label should be 'Bull Analyst'."""
    mock_lang.return_value = ""
    llm = _mock_llm("bullish argument")
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state())

    current_response = result["investment_debate_state"]["current_response"]
    assert current_response.startswith("Bull Analyst:")


# ---------------------------------------------------------------------------
# State update format
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_returns_investment_debate_state_key(mock_lang):
    """The returned dict must have 'investment_debate_state' as the only key."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state())

    assert "investment_debate_state" in result
    assert set(result.keys()) == {"investment_debate_state"}


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_investment_debate_state_has_required_keys(mock_lang):
    """The investment_debate_state dict must contain all required keys."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state())

    debate_state = result["investment_debate_state"]
    expected_keys = {"history", "bull_history", "bear_history", "current_response", "count"}
    assert set(debate_state.keys()) == expected_keys


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_count_incremented_by_one(mock_lang):
    """The count in the returned state should be incremented by 1."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state(count=3))

    assert result["investment_debate_state"]["count"] == 4


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_history_appended_with_argument(mock_lang):
    """The history should be the previous history plus the new argument."""
    mock_lang.return_value = ""
    llm = _mock_llm("great stock")
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state(history="previous debate"))

    history = result["investment_debate_state"]["history"]
    assert "previous debate" in history
    assert "Bull Analyst: great stock" in history


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_bull_history_appended(mock_lang):
    """bull_history should be the previous bull_history plus the new argument."""
    mock_lang.return_value = ""
    llm = _mock_llm("strong buy")
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state(bull_history="earlier bull point"))

    bull_history = result["investment_debate_state"]["bull_history"]
    assert "earlier bull point" in bull_history
    assert "Bull Analyst: strong buy" in bull_history


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_bear_history_preserved_unchanged(mock_lang):
    """bear_history should be passed through unchanged."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state(bear_history="bear said something"))

    assert result["investment_debate_state"]["bear_history"] == "bear said something"


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_current_response_is_labeled_argument(mock_lang):
    """current_response should be 'Label: llm_content'."""
    mock_lang.return_value = ""
    llm = _mock_llm("momentum is strong")
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state())

    assert (
        result["investment_debate_state"]["current_response"] == "Bull Analyst: momentum is strong"
    )


# ---------------------------------------------------------------------------
# Memory integration
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_memory_get_memories_called_with_situation(mock_lang):
    """memory.get_memories should be called with the combined situation string."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    bull_node(
        _make_state(
            market_report="MR",
            sentiment_report="SR",
            news_report="NR",
            fundamentals_report="FR",
        )
    )

    memory.get_memories.assert_called_once()
    call_args = memory.get_memories.call_args
    situation_arg = call_args[0][0]
    assert "MR" in situation_arg
    assert "SR" in situation_arg
    assert "NR" in situation_arg
    assert "FR" in situation_arg


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_memory_get_memories_n_matches_2(mock_lang):
    """memory.get_memories should request n_matches=2."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    bull_node(_make_state())

    memory.get_memories.assert_called_once_with(
        memory.get_memories.call_args[0][0],
        n_matches=2,
    )


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_past_memories_included_in_prompt(mock_lang):
    """When memories are returned, their recommendations should appear in the LLM prompt."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memories = [
        {"recommendation": "Previously, buying at dips worked well."},
        {"recommendation": "Avoid chasing momentum blindly."},
    ]
    memory = _mock_memory(memories)

    bull_node = create_bull_researcher(llm, memory)
    bull_node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Previously, buying at dips worked well." in prompt
    assert "Avoid chasing momentum blindly." in prompt


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_empty_memories_no_error(mock_lang):
    """When no memories are returned, the function should still work."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory([])

    bull_node = create_bull_researcher(llm, memory)
    result = bull_node(_make_state())

    assert "investment_debate_state" in result


# ---------------------------------------------------------------------------
# LLM invocation
# ---------------------------------------------------------------------------


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_llm_invoke_called_once(mock_lang):
    """llm.invoke should be called exactly once per bull_node call."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    bull_node(_make_state())

    llm.invoke.assert_called_once()


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_llm_prompt_contains_bull_analyst_role(mock_lang):
    """The prompt sent to the LLM should mention the Bull Analyst role."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    bull_node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Bull Analyst" in prompt


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_llm_prompt_contains_state_reports(mock_lang):
    """The prompt should include all four report types from state."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    bull_node(
        _make_state(
            market_report="MARKET_DATA_123",
            sentiment_report="SENTIMENT_DATA_456",
            news_report="NEWS_DATA_789",
            fundamentals_report="FUNDAMENTALS_DATA_012",
        )
    )

    prompt = llm.invoke.call_args[0][0]
    assert "MARKET_DATA_123" in prompt
    assert "SENTIMENT_DATA_456" in prompt
    assert "NEWS_DATA_789" in prompt
    assert "FUNDAMENTALS_DATA_012" in prompt


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_llm_prompt_contains_current_response(mock_lang):
    """The prompt should include the bear's last argument (current_response)."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    bull_node(_make_state(current_response="Bear says: too risky"))

    prompt = llm.invoke.call_args[0][0]
    assert "Bear says: too risky" in prompt


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_llm_prompt_contains_language_instruction_chinese(mock_lang):
    """When in Chinese mode, the language instruction should be appended to the prompt."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    bull_node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Write your entire response in Chinese." in prompt


@patch("tradingagents.agents.researchers.bull_researcher.get_language_instruction")
def test_llm_prompt_no_language_instruction_english(mock_lang):
    """When in English mode, no language instruction should be appended."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    bull_node = create_bull_researcher(llm, memory)
    bull_node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Write your entire response in" not in prompt


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def test_create_bull_researcher_returns_callable():
    """create_bull_researcher should return a callable."""
    llm = _mock_llm()
    memory = _mock_memory()

    result = create_bull_researcher(llm, memory)
    assert callable(result)
