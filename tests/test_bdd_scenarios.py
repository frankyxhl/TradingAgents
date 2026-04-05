# tests/test_bdd_scenarios.py
"""
BDD scenarios for TradingAgents Livermore fork (CHG-2001).

Five behavioral tests covering:
  1. Provider routing  — ZAI endpoint configuration
  2. Chinese localization — agent label language
  3. Report rendering  — Chinese action labels in HTML
  4. Graph routing     — debate routing with Chinese prefixes
  5. End-to-end mock   — signal processing produces valid decision

All LLM calls are mocked. No network access required.
"""

import re
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when

# ---------------------------------------------------------------------------
# Scenario 1: Provider routing
# ---------------------------------------------------------------------------


@scenario("features/provider_routing.feature", "ZAI provider uses Z.AI Coding API endpoint")
def test_zai_provider_routing():
    pass


@scenario("features/provider_routing.feature", "XAI provider uses xAI endpoint")
def test_xai_provider_routing():
    pass


@pytest.fixture
def provider_context():
    """Shared mutable context for provider routing steps."""
    return {}


@given(parsers.parse('provider "{provider}"'), target_fixture="provider_context")
def given_provider(provider):
    return {"provider": provider}


@when("creating an LLM client", target_fixture="llm_client")
def create_llm_client(provider_context):
    from tradingagents.llm_clients.openai_client import OpenAIClient

    provider = provider_context["provider"]
    # Use a dummy model; we only inspect the base_url, not actually call the API
    client = OpenAIClient(model="test-model", provider=provider, api_key="fake-key")

    # Patch the ChatOpenAI constructor so get_llm() doesn't hit the network
    with patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI") as MockLLM:
        mock_instance = MagicMock()
        MockLLM.return_value = mock_instance
        client.get_llm()
        # Capture the kwargs passed to NormalizedChatOpenAI
        return {"call_kwargs": MockLLM.call_args}


@then(parsers.parse('the client should use the endpoint "{endpoint}"'))
def verify_endpoint(llm_client, endpoint):
    call_kwargs = llm_client["call_kwargs"]
    # NormalizedChatOpenAI receives base_url as a keyword argument
    _, kwargs = call_kwargs
    assert kwargs["base_url"] == endpoint, (
        f"Expected base_url={endpoint!r}, got {kwargs.get('base_url')!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 2: Chinese localization
# ---------------------------------------------------------------------------


@scenario(
    "features/chinese_localization.feature",
    "Bull analyst label is Chinese when language is Chinese",
)
def test_chinese_bull_label():
    pass


@given(parsers.parse('output_language is "{language}"'), target_fixture="language_config")
def set_output_language(language):
    return {"language": language}


@when("an agent generates a bull analyst label", target_fixture="bull_label")
def generate_bull_label(language_config):
    from tradingagents.agents.utils.agent_utils import get_language_instruction
    from tradingagents.dataflows.config import get_config, set_config

    # Save original config so we can restore it
    original = get_config()
    try:
        set_config({"output_language": language_config["language"]})

        # Call the real source function instead of duplicating its logic
        get_language_instruction()  # ensure config is active
        # Import label strings from the source module so this test stays
        # in sync if the strings ever change
        from tradingagents.agents.researchers.bull_researcher import create_bull_researcher

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "strong buy argument"
        mock_llm.invoke.return_value = mock_response

        mock_memory = MagicMock()
        mock_memory.get_memories.return_value = []

        bull_node = create_bull_researcher(mock_llm, mock_memory)
        state = {
            "investment_debate_state": {
                "count": 0,
                "current_response": "",
                "bull_history": "",
                "bear_history": "",
                "history": "",
                "judge_decision": "",
            },
            "market_report": "",
            "sentiment_report": "",
            "news_report": "",
            "fundamentals_report": "",
        }
        result = bull_node(state)
        current_response = result["investment_debate_state"]["current_response"]
        # The response is formatted as "<label>: <content>" — extract the label
        label = current_response.split(":")[0].strip()
        return {"label": label}
    finally:
        set_config(original)


@then(parsers.parse('the label should be in Chinese as "{expected}"'))
def verify_chinese_label(bull_label, expected):
    assert bull_label["label"] == expected, (
        f"Expected label={expected!r}, got {bull_label['label']!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 3: Report rendering
# ---------------------------------------------------------------------------


@scenario(
    "features/report_rendering.feature",
    "Chinese buy action renders in HTML",
)
def test_chinese_report_rendering():
    pass


@given(
    parsers.parse('a trading report with action "{action}"'),
    target_fixture="report_data",
)
def report_with_action(action):
    """Build a minimal report dict whose final_trade_decision contains the action."""
    return {
        "trade_date": "2026-04-04",
        "company_of_interest": "AAPL",
        "final_trade_decision": f"最终交易建议：**{action}**\n分析完毕。",
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
    }


@when("rendered to HTML", target_fixture="rendered_html")
def render_to_html(report_data):
    from tradingagents.render_report import render_html

    html = render_html(report_data)
    return {"html": html}


@then(parsers.parse('the HTML should contain the Chinese action label "{label}"'))
def html_contains_chinese_label(rendered_html, label):
    assert label in rendered_html["html"], f"Expected Chinese label {label!r} in HTML output"


@then(parsers.parse('should not contain untranslated English label "{eng}" in the badge'))
def html_badge_no_english(rendered_html, eng):
    html = rendered_html["html"]
    # Extract the badge element specifically
    badge_match = re.search(r'<div class="badge[^"]*">([^<]+)</div>', html)
    assert badge_match, "No badge element found in HTML"
    badge_text = badge_match.group(1)
    assert eng not in badge_text, (
        f"Badge should not contain English label {eng!r}, but badge text is {badge_text!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 4: Graph routing
# ---------------------------------------------------------------------------


@scenario(
    "features/graph_routing.feature",
    "Chinese bull response routes to Bear Researcher",
)
def test_chinese_debate_routing():
    pass


@scenario(
    "features/graph_routing.feature",
    "English bull response routes to Bear Researcher",
)
def test_english_debate_routing():
    pass


def _build_debate_state(speaker):
    return {
        "investment_debate_state": {
            "count": 1,  # below the 2*max threshold so debate continues
            "current_response": f"{speaker}: This stock has great potential.",
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "judge_decision": "",
        }
    }


@given(
    parsers.parse('a Chinese debate response from "{speaker}"'),
    target_fixture="debate_state",
)
def debate_response_chinese(speaker):
    return _build_debate_state(speaker)


@given(
    parsers.parse('a debate response from "{speaker}"'),
    target_fixture="debate_state",
)
def debate_response_english(speaker):
    return _build_debate_state(speaker)


@when("routing to the next node", target_fixture="next_node")
def route_to_next_node(debate_state):
    from tradingagents.graph.conditional_logic import ConditionalLogic

    logic = ConditionalLogic(max_debate_rounds=2, max_risk_discuss_rounds=1)
    result = logic.should_continue_debate(debate_state)
    return {"node": result}


@then(parsers.parse('the next node should be "{expected}"'))
def verify_next_node(next_node, expected):
    assert next_node["node"] == expected, (
        f"Expected next node={expected!r}, got {next_node['node']!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 5: End-to-end mock pipeline (signal processing)
# ---------------------------------------------------------------------------


@scenario(
    "features/end_to_end_mock.feature",
    "Pipeline produces a valid trading decision",
)
def test_e2e_signal_processing():
    pass


@given(
    "a complete trading pipeline with mocked LLM",
    target_fixture="mock_pipeline",
)
def mock_pipeline():
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "BUY"
    mock_llm.invoke.return_value = mock_response

    from tradingagents.graph.signal_processing import SignalProcessor

    processor = SignalProcessor(quick_thinking_llm=mock_llm)
    return {"processor": processor, "mock_llm": mock_llm}


@when(
    parsers.parse('the pipeline processes ticker "{ticker}"'),
    target_fixture="pipeline_result",
)
def process_ticker(mock_pipeline, ticker):
    processor = mock_pipeline["processor"]
    # Build a synthetic analyst report mentioning the ticker
    signal_text = (
        f"After thorough analysis of {ticker}, considering strong revenue growth "
        "and favorable market conditions, our recommendation is to BUY."
    )
    decision = processor.process_signal(signal_text)
    return {"decision": decision, "ticker": ticker}


@then("a trading decision should be produced")
def decision_produced(pipeline_result):
    assert pipeline_result["decision"] is not None
    assert len(pipeline_result["decision"].strip()) > 0, "Decision should not be empty"


@then("the decision should contain BUY, SELL, or HOLD")
def decision_valid(pipeline_result):
    decision = pipeline_result["decision"].upper().strip()
    valid = {"BUY", "SELL", "HOLD", "OVERWEIGHT", "UNDERWEIGHT"}
    assert decision in valid, f"Decision {decision!r} not in valid set {valid}"
