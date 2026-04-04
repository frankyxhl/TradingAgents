# tests/test_research_manager.py
"""
Tests for tradingagents/agents/managers/research_manager.py

Covers the create_research_manager factory and the inner research_manager_node,
including language instruction injection, state update format, memory integration,
and LLM invocation with debate context.
"""

from unittest.mock import patch, MagicMock

import pytest

from tradingagents.agents.managers.research_manager import create_research_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    company_of_interest="AAPL",
    market_report="market report",
    sentiment_report="sentiment report",
    news_report="news report",
    fundamentals_report="fundamentals report",
    history="",
    bull_history="",
    bear_history="",
    current_response="",
    count=0,
    judge_decision="",
):
    """Build a minimal state dict matching what research_manager_node expects."""
    return {
        "company_of_interest": company_of_interest,
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
            "judge_decision": judge_decision,
        },
    }


def _mock_llm(response_content="Buy recommendation with strong conviction."):
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
# Language instruction injection
# ---------------------------------------------------------------------------

@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_chinese_language_instruction_in_prompt(mock_lang):
    """When output_language=Chinese, the language instruction appears in the prompt."""
    mock_lang.return_value = " Write your entire response in Chinese."
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Write your entire response in Chinese." in prompt


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_no_language_instruction_in_english(mock_lang):
    """When output_language=English, no language instruction is appended."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Write your entire response in" not in prompt


# ---------------------------------------------------------------------------
# State update format
# ---------------------------------------------------------------------------

@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_returns_correct_top_level_keys(mock_lang):
    """Returned dict must contain 'investment_debate_state' and 'investment_plan'."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state())

    assert set(result.keys()) == {"investment_debate_state", "investment_plan"}


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_investment_debate_state_has_required_keys(mock_lang):
    """The investment_debate_state must contain all required keys."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state())

    debate_state = result["investment_debate_state"]
    expected_keys = {
        "judge_decision", "history", "bear_history",
        "bull_history", "current_response", "count",
    }
    assert set(debate_state.keys()) == expected_keys


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_judge_decision_set_to_llm_response(mock_lang):
    """judge_decision should be set to the LLM response content."""
    mock_lang.return_value = ""
    llm = _mock_llm("Sell - too much risk")
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state())

    assert result["investment_debate_state"]["judge_decision"] == "Sell - too much risk"


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_current_response_set_to_llm_response(mock_lang):
    """current_response should be set to the LLM response content."""
    mock_lang.return_value = ""
    llm = _mock_llm("Hold for now")
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state())

    assert result["investment_debate_state"]["current_response"] == "Hold for now"


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_investment_plan_set_to_llm_response(mock_lang):
    """investment_plan should be set to the LLM response content."""
    mock_lang.return_value = ""
    llm = _mock_llm("Buy with 60% position")
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state())

    assert result["investment_plan"] == "Buy with 60% position"


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_count_preserved_from_input_state(mock_lang):
    """The count should be passed through unchanged from the input state."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state(count=5))

    assert result["investment_debate_state"]["count"] == 5


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_history_preserved_from_input_state(mock_lang):
    """The history should be passed through unchanged from the input state."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state(history="round 1 debate"))

    assert result["investment_debate_state"]["history"] == "round 1 debate"


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_bull_history_preserved(mock_lang):
    """bull_history should be passed through unchanged."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state(bull_history="bull said growth"))

    assert result["investment_debate_state"]["bull_history"] == "bull said growth"


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_bear_history_preserved(mock_lang):
    """bear_history should be passed through unchanged."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    result = node(_make_state(bear_history="bear said decline"))

    assert result["investment_debate_state"]["bear_history"] == "bear said decline"


# ---------------------------------------------------------------------------
# LLM invocation with debate context
# ---------------------------------------------------------------------------

@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_llm_invoke_called_once(mock_lang):
    """llm.invoke should be called exactly once."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    node(_make_state())

    llm.invoke.assert_called_once()


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_prompt_contains_debate_history(mock_lang):
    """The prompt should include the debate history from state."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    node(_make_state(history="Bull: strong growth. Bear: high risk."))

    prompt = llm.invoke.call_args[0][0]
    assert "Bull: strong growth. Bear: high risk." in prompt


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_prompt_contains_instrument_context(mock_lang):
    """The prompt should include the instrument context with the ticker."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    node(_make_state(company_of_interest="TSLA"))

    prompt = llm.invoke.call_args[0][0]
    assert "TSLA" in prompt


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_prompt_mentions_facilitator_role(mock_lang):
    """The prompt should mention the portfolio manager / debate facilitator role."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "portfolio manager" in prompt.lower() or "debate facilitator" in prompt.lower()


# ---------------------------------------------------------------------------
# Memory integration
# ---------------------------------------------------------------------------

@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_memory_get_memories_called(mock_lang):
    """memory.get_memories should be called with n_matches=2."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    node(_make_state())

    memory.get_memories.assert_called_once()
    call_kwargs = memory.get_memories.call_args[1]
    assert call_kwargs.get("n_matches") == 2


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_memory_situation_includes_reports(mock_lang):
    """The situation string passed to memory should include all four reports."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory()

    node = create_research_manager(llm, memory)
    node(_make_state(
        market_report="MR_UNIQUE",
        sentiment_report="SR_UNIQUE",
        news_report="NR_UNIQUE",
        fundamentals_report="FR_UNIQUE",
    ))

    situation_arg = memory.get_memories.call_args[0][0]
    assert "MR_UNIQUE" in situation_arg
    assert "SR_UNIQUE" in situation_arg
    assert "NR_UNIQUE" in situation_arg
    assert "FR_UNIQUE" in situation_arg


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_past_memories_included_in_prompt(mock_lang):
    """When memories are returned, their recommendations appear in the LLM prompt."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memories = [
        {"recommendation": "Lesson: do not chase momentum."},
        {"recommendation": "Lesson: hedge with puts."},
    ]
    memory = _mock_memory(memories)

    node = create_research_manager(llm, memory)
    node(_make_state())

    prompt = llm.invoke.call_args[0][0]
    assert "Lesson: do not chase momentum." in prompt
    assert "Lesson: hedge with puts." in prompt


@patch("tradingagents.agents.managers.research_manager.get_language_instruction")
def test_empty_memories_no_error(mock_lang):
    """When no memories exist, the function should still work without error."""
    mock_lang.return_value = ""
    llm = _mock_llm()
    memory = _mock_memory([])

    node = create_research_manager(llm, memory)
    result = node(_make_state())

    assert "investment_debate_state" in result
    assert "investment_plan" in result


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def test_create_research_manager_returns_callable():
    """create_research_manager should return a callable."""
    llm = _mock_llm()
    memory = _mock_memory()

    result = create_research_manager(llm, memory)
    assert callable(result)
