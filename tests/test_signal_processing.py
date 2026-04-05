# tests/test_signal_processing.py
"""
Tests for tradingagents/graph/signal_processing.py

SignalProcessor wraps an LLM call; all tests mock the LLM so no real
API calls are made.
"""

from unittest.mock import MagicMock

from tradingagents.graph.signal_processing import SignalProcessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_processor(return_content="BUY"):
    """Build a SignalProcessor backed by a mocked LLM."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=return_content)
    return SignalProcessor(quick_thinking_llm=mock_llm), mock_llm


# ---------------------------------------------------------------------------
# Basic signal parsing — happy path
# ---------------------------------------------------------------------------


def test_process_signal_returns_buy():
    processor, _ = _make_processor("BUY")
    assert processor.process_signal("Strong bullish momentum") == "BUY"


def test_process_signal_returns_sell():
    processor, _ = _make_processor("SELL")
    assert processor.process_signal("Company fundamentals deteriorating badly") == "SELL"


def test_process_signal_returns_hold():
    processor, _ = _make_processor("HOLD")
    assert processor.process_signal("Mixed signals, no clear direction") == "HOLD"


def test_process_signal_returns_overweight():
    processor, _ = _make_processor("OVERWEIGHT")
    assert processor.process_signal("Slightly bullish, recommend overweight") == "OVERWEIGHT"


def test_process_signal_returns_underweight():
    processor, _ = _make_processor("UNDERWEIGHT")
    assert (
        processor.process_signal("Slight caution, recommend underweight position") == "UNDERWEIGHT"
    )


# ---------------------------------------------------------------------------
# LLM is invoked with the correct message structure
# ---------------------------------------------------------------------------


def test_process_signal_passes_signal_as_human_message():
    processor, mock_llm = _make_processor("HOLD")
    signal_text = "Revenue growth slowing but margins stable."
    processor.process_signal(signal_text)

    call_args = mock_llm.invoke.call_args
    messages = call_args[0][0]  # first positional arg

    # The second tuple must be the human message containing the signal text
    human_role, human_content = messages[1]
    assert human_role == "human"
    assert human_content == signal_text


def test_process_signal_includes_system_message():
    processor, mock_llm = _make_processor("BUY")
    processor.process_signal("Any signal text")

    call_args = mock_llm.invoke.call_args
    messages = call_args[0][0]

    system_role, system_content = messages[0]
    assert system_role == "system"
    # System message should mention rating extraction
    assert "BUY" in system_content or "rating" in system_content.lower()


def test_process_signal_sends_exactly_two_messages():
    processor, mock_llm = _make_processor("SELL")
    processor.process_signal("Some signal")

    messages = mock_llm.invoke.call_args[0][0]
    assert len(messages) == 2


def test_process_signal_llm_invoked_exactly_once():
    processor, mock_llm = _make_processor("BUY")
    processor.process_signal("First call")
    assert mock_llm.invoke.call_count == 1


# ---------------------------------------------------------------------------
# Return value is exactly the LLM .content attribute
# ---------------------------------------------------------------------------


def test_process_signal_returns_llm_content_verbatim():
    """Whatever .content the LLM returns is returned as-is (no trimming/wrapping)."""
    processor, _ = _make_processor("OVERWEIGHT")
    result = processor.process_signal("Positive outlook")
    assert result == "OVERWEIGHT"


def test_process_signal_returns_raw_string_from_llm():
    """If LLM returns unexpected content, it is passed through unchanged."""
    processor, _ = _make_processor("  BUY  ")  # with whitespace
    result = processor.process_signal("Signal with spaces")
    assert result == "  BUY  "


# ---------------------------------------------------------------------------
# Edge cases — empty / degenerate inputs
# ---------------------------------------------------------------------------


def test_process_signal_empty_string_input():
    """Empty input should still call the LLM and return its content."""
    processor, mock_llm = _make_processor("HOLD")
    result = processor.process_signal("")
    assert mock_llm.invoke.called
    assert result == "HOLD"


def test_process_signal_whitespace_only_input():
    processor, mock_llm = _make_processor("HOLD")
    result = processor.process_signal("   ")
    assert mock_llm.invoke.called
    assert result == "HOLD"


def test_process_signal_very_long_input():
    """Very long signal text should be passed to the LLM without truncation."""
    processor, mock_llm = _make_processor("SELL")
    long_signal = "This is a very detailed report. " * 500
    processor.process_signal(long_signal)

    messages = mock_llm.invoke.call_args[0][0]
    _, human_content = messages[1]
    assert human_content == long_signal


def test_process_signal_chinese_input():
    """Chinese-language signals (common in livermore fork) must be passed through."""
    processor, mock_llm = _make_processor("BUY")
    chinese_signal = "公司基本面强劲，建议买入。市盈率低于行业平均水平。"
    processor.process_signal(chinese_signal)

    messages = mock_llm.invoke.call_args[0][0]
    _, human_content = messages[1]
    assert human_content == chinese_signal


# ---------------------------------------------------------------------------
# Constructor — LLM is stored correctly
# ---------------------------------------------------------------------------


def test_constructor_stores_llm():
    mock_llm = MagicMock()
    processor = SignalProcessor(quick_thinking_llm=mock_llm)
    assert processor.quick_thinking_llm is mock_llm


def test_constructor_different_llm_instances_are_independent():
    mock_llm_a = MagicMock()
    mock_llm_b = MagicMock()
    processor_a = SignalProcessor(quick_thinking_llm=mock_llm_a)
    processor_b = SignalProcessor(quick_thinking_llm=mock_llm_b)
    assert processor_a.quick_thinking_llm is not processor_b.quick_thinking_llm
