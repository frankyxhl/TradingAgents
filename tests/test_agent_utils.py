"""Tests for tradingagents/agents/utils/agent_utils.py"""

from unittest.mock import patch

# ---------------------------------------------------------------------------
# get_language_instruction
# ---------------------------------------------------------------------------


def test_get_language_instruction_english_returns_empty_string():
    """English (the default) should produce no extra tokens."""
    with patch(
        "tradingagents.dataflows.config.get_config", return_value={"output_language": "English"}
    ):
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        result = get_language_instruction()
    assert result == ""


def test_get_language_instruction_english_case_insensitive():
    """'english' (lowercase) must also return empty string."""
    with patch(
        "tradingagents.dataflows.config.get_config", return_value={"output_language": "english"}
    ):
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        result = get_language_instruction()
    assert result == ""


def test_get_language_instruction_english_with_whitespace():
    """Leading/trailing whitespace around 'English' must still return empty."""
    with patch(
        "tradingagents.dataflows.config.get_config", return_value={"output_language": "  English  "}
    ):
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        result = get_language_instruction()
    assert result == ""


def test_get_language_instruction_chinese_contains_language_name():
    """Chinese output_language should embed the language name in the instruction."""
    with patch(
        "tradingagents.dataflows.config.get_config", return_value={"output_language": "Chinese"}
    ):
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        result = get_language_instruction()
    assert "Chinese" in result
    assert len(result) > 0


def test_get_language_instruction_chinese_is_non_empty():
    """Chinese output should produce a non-empty instruction string."""
    with patch(
        "tradingagents.dataflows.config.get_config", return_value={"output_language": "Chinese"}
    ):
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        result = get_language_instruction()
    assert result.strip() != ""


def test_get_language_instruction_arbitrary_language():
    """Any non-English language should embed the language name."""
    with patch(
        "tradingagents.dataflows.config.get_config", return_value={"output_language": "Japanese"}
    ):
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        result = get_language_instruction()
    assert "Japanese" in result


def test_get_language_instruction_missing_key_defaults_to_english():
    """If output_language key is absent the function should return empty string."""
    with patch("tradingagents.dataflows.config.get_config", return_value={}):
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        result = get_language_instruction()
    assert result == ""


# ---------------------------------------------------------------------------
# build_instrument_context
# ---------------------------------------------------------------------------


def test_build_instrument_context_contains_ticker():
    """The returned string must contain the exact ticker passed in."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("AAPL")
    assert "AAPL" in result


def test_build_instrument_context_exchange_suffix_preserved():
    """A ticker with an exchange suffix must appear verbatim in the output."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("7203.T")
    assert "7203.T" in result


def test_build_instrument_context_mentions_exchange_suffix():
    """Output must mention exchange suffixes so agents know to preserve them."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("RY.TO")
    assert "exchange suffix" in result.lower() or "exchange" in result.lower()


def test_build_instrument_context_toronto_stock():
    """Toronto-listed ticker (.TO suffix) should appear verbatim."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("CNC.TO")
    assert "CNC.TO" in result


def test_build_instrument_context_london_stock():
    """London-listed ticker (.L suffix) should appear verbatim."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("HSBA.L")
    assert "HSBA.L" in result


def test_build_instrument_context_hong_kong_stock():
    """Hong Kong ticker (.HK suffix) should appear verbatim."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("0700.HK")
    assert "0700.HK" in result


def test_build_instrument_context_returns_string():
    """Return type must be str."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("TSLA")
    assert isinstance(result, str)


def test_build_instrument_context_non_empty():
    """Result must not be empty."""
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    result = build_instrument_context("TSLA")
    assert len(result.strip()) > 0


# ---------------------------------------------------------------------------
# create_msg_delete
# ---------------------------------------------------------------------------


def test_create_msg_delete_returns_callable():
    """create_msg_delete() must return a callable."""
    from tradingagents.agents.utils.agent_utils import create_msg_delete

    fn = create_msg_delete()
    assert callable(fn)


def test_create_msg_delete_result_contains_messages_key():
    """The inner function must return a dict with 'messages' key."""
    from langchain_core.messages import HumanMessage

    from tradingagents.agents.utils.agent_utils import create_msg_delete

    msg = HumanMessage(content="hello")
    state = {"messages": [msg]}

    fn = create_msg_delete()
    result = fn(state)
    assert "messages" in result


def test_create_msg_delete_adds_placeholder():
    """The returned messages list must include a HumanMessage placeholder."""
    from langchain_core.messages import HumanMessage

    from tradingagents.agents.utils.agent_utils import create_msg_delete

    msg = HumanMessage(content="original message")
    state = {"messages": [msg]}

    fn = create_msg_delete()
    result = fn(state)
    human_messages = [m for m in result["messages"] if isinstance(m, HumanMessage)]
    assert len(human_messages) >= 1
    assert human_messages[-1].content == "Continue"


def test_create_msg_delete_generates_remove_operations():
    """The result should include RemoveMessage operations for existing messages."""
    from langchain_core.messages import HumanMessage, RemoveMessage

    from tradingagents.agents.utils.agent_utils import create_msg_delete

    msg1 = HumanMessage(content="msg1")
    msg2 = HumanMessage(content="msg2")
    state = {"messages": [msg1, msg2]}

    fn = create_msg_delete()
    result = fn(state)
    remove_ops = [m for m in result["messages"] if isinstance(m, RemoveMessage)]
    assert len(remove_ops) == 2


def test_create_msg_delete_empty_messages():
    """create_msg_delete should handle an empty messages list without error."""
    from tradingagents.agents.utils.agent_utils import create_msg_delete

    state = {"messages": []}
    fn = create_msg_delete()
    result = fn(state)
    assert "messages" in result
