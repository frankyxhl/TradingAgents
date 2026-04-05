"""Tests for render_report.py (project root)."""

import os
import sys

# Ensure project root is on sys.path so `import render_report` works
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from render_report import inline_md, md_to_html, render_html  # noqa: E402

# ---------------------------------------------------------------------------
# inline_md
# ---------------------------------------------------------------------------


def test_inline_md_bold_asterisks():
    assert inline_md("**hello**") == "<strong>hello</strong>"


def test_inline_md_bold_underscores():
    assert inline_md("__world__") == "<strong>world</strong>"


def test_inline_md_italic():
    assert inline_md("*italic*") == "<em>italic</em>"


def test_inline_md_code():
    assert inline_md("`code`") == "<code>code</code>"


def test_inline_md_no_markdown():
    text = "plain text"
    assert inline_md(text) == text


def test_inline_md_mixed():
    result = inline_md("**bold** and *italic*")
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result


def test_inline_md_nested_code_in_bold():
    result = inline_md("**`ticker`**")
    # bold wraps the code tag
    assert "<strong>" in result


# ---------------------------------------------------------------------------
# md_to_html
# ---------------------------------------------------------------------------


def test_md_to_html_heading_h1():
    result = md_to_html("# Title")
    assert "<h1>Title</h1>" in result


def test_md_to_html_heading_h2():
    result = md_to_html("## Section")
    assert "<h2>Section</h2>" in result


def test_md_to_html_heading_h3():
    result = md_to_html("### Sub")
    assert "<h3>Sub</h3>" in result


def test_md_to_html_paragraph():
    result = md_to_html("Hello world")
    assert "<p>Hello world</p>" in result


def test_md_to_html_unordered_list():
    result = md_to_html("- item one\n- item two")
    assert "<ul>" in result
    assert "<li>item one</li>" in result
    assert "<li>item two</li>" in result


def test_md_to_html_unordered_list_asterisk():
    result = md_to_html("* first\n* second")
    assert "<ul>" in result
    assert "<li>first</li>" in result


def test_md_to_html_ordered_list():
    result = md_to_html("1. alpha\n2. beta")
    assert "<ul>" in result
    assert "<li>alpha</li>" in result


def test_md_to_html_horizontal_rule():
    result = md_to_html("---")
    assert "<hr>" in result


def test_md_to_html_horizontal_rule_asterisks():
    result = md_to_html("***")
    assert "<hr>" in result


def test_md_to_html_table():
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = md_to_html(md)
    assert "<table>" in result
    assert "<th>A</th>" in result
    assert "<td>1</td>" in result


def test_md_to_html_empty_string():
    result = md_to_html("")
    assert result == ""


def test_md_to_html_blank_lines_close_list():
    md = "- item\n\nAfter list"
    result = md_to_html(md)
    assert "</ul>" in result
    assert "<p>After list</p>" in result


def test_md_to_html_bold_inline_in_paragraph():
    result = md_to_html("This is **important**.")
    assert "<strong>important</strong>" in result


# ---------------------------------------------------------------------------
# render_html — action extraction (English format)
# ---------------------------------------------------------------------------


def _minimal_data(decision: str) -> dict:
    return {
        "trade_date": "2025-01-01",
        "company_of_interest": "AAPL",
        "final_trade_decision": decision,
    }


def test_render_html_english_buy_action():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: **BUY**")
    html = render_html(data)
    assert 'class="badge buy"' in html


def test_render_html_english_sell_action():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: SELL")
    html = render_html(data)
    assert 'class="badge sell"' in html


def test_render_html_english_hold_action():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: HOLD")
    html = render_html(data)
    assert 'class="badge hold"' in html


def test_render_html_english_action_case_insensitive_in_badge():
    """Badge class should be lowercase regardless of extracted action."""
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    html = render_html(data)
    assert 'class="badge buy"' in html


# ---------------------------------------------------------------------------
# render_html — action extraction (Chinese format)
# ---------------------------------------------------------------------------


def test_render_html_chinese_buy_action():
    data = _minimal_data("最终交易建议：**买入**")
    html = render_html(data)
    assert 'class="badge buy"' in html


def test_render_html_chinese_sell_action():
    data = _minimal_data("最终交易建议：**卖出**")
    html = render_html(data)
    assert 'class="badge sell"' in html


def test_render_html_chinese_hold_action():
    data = _minimal_data("最终交易建议：持有")
    html = render_html(data)
    assert 'class="badge hold"' in html


def test_render_html_chinese_overweight_action():
    data = _minimal_data("最终交易建议：增持")
    html = render_html(data)
    assert 'class="badge buy"' in html


def test_render_html_chinese_underweight_action():
    data = _minimal_data("最终交易建议：减持")
    html = render_html(data)
    assert 'class="badge sell"' in html


def test_render_html_chinese_colon_variants():
    """Both full-width and half-width colons after 最终交易建议 should be matched."""
    data_fw = _minimal_data("最终交易建议：买入")
    data_hw = _minimal_data("最终交易建议:买入")
    html_fw = render_html(data_fw)
    html_hw = render_html(data_hw)
    assert 'class="badge buy"' in html_fw
    assert 'class="badge buy"' in html_hw


# ---------------------------------------------------------------------------
# render_html — fallback keyword scan
# ---------------------------------------------------------------------------


def test_render_html_fallback_chinese_keyword_buy():
    """Fallback: 建议买入 in tail should resolve to BUY."""
    data = _minimal_data("分析结果显示 建议买入")
    html = render_html(data)
    assert 'class="badge buy"' in html


def test_render_html_fallback_chinese_keyword_sell():
    data = _minimal_data("综合评估：建议卖出")
    html = render_html(data)
    assert 'class="badge sell"' in html


def test_render_html_fallback_english_keyword_in_tail():
    """Fallback: plain SELL in tail (no structured prefix)."""
    data = _minimal_data("After analysis the answer is SELL")
    html = render_html(data)
    assert 'class="badge sell"' in html


def test_render_html_fallback_unknown_action_defaults_hold_class():
    """Unknown action should not crash; badge class defaults to hold."""
    data = _minimal_data("")
    html = render_html(data)
    assert "badge" in html


# ---------------------------------------------------------------------------
# render_html — structure and metadata
# ---------------------------------------------------------------------------


def test_render_html_contains_ticker_in_title():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    html = render_html(data)
    assert "AAPL" in html


def test_render_html_contains_trade_date():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    html = render_html(data)
    assert "2025-01-01" in html


def test_render_html_is_valid_html_skeleton():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    html = render_html(data)
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html


def test_render_html_contains_analyst_sections():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    data["market_report"] = "Market is up."
    html = render_html(data)
    assert "技术分析" in html


def test_render_html_optional_sections_absent_by_default():
    """If investment_debate_state is absent, debate section should not appear."""
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    html = render_html(data)
    # The nav link for debate should not appear when no debate data is present
    assert "投资辩论" not in html


def test_render_html_debate_section_present_when_bull_history():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    data["investment_debate_state"] = {
        "bull_history": "Bulls are optimistic.",
        "bear_history": "",
        "judge_decision": "",
    }
    html = render_html(data)
    assert "看多观点" in html


def test_render_html_risk_section_present_when_aggressive_history():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    data["risk_debate_state"] = {
        "aggressive_history": "High risk appetite.",
        "conservative_history": "",
        "neutral_history": "",
        "judge_decision": "",
    }
    html = render_html(data)
    assert "激进观点" in html


def test_render_html_trader_plan_section():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: HOLD")
    data["trader_investment_decision"] = "Hold for now."
    html = render_html(data)
    assert "交易员决策" in html


# ---------------------------------------------------------------------------
# flatten (accessed via render_html with list values)
# ---------------------------------------------------------------------------


def test_render_html_flatten_list_bull_history():
    """flatten() inside render_html should join list elements with double newline."""
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    data["investment_debate_state"] = {
        "bull_history": ["Point A", "Point B"],
        "bear_history": [],
        "judge_decision": "",
    }
    html = render_html(data)
    assert "Point A" in html
    assert "Point B" in html


def test_render_html_flatten_single_string_unchanged():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: HOLD")
    data["investment_debate_state"] = {
        "bull_history": "Single string value.",
        "bear_history": "",
        "judge_decision": "",
    }
    html = render_html(data)
    assert "Single string value." in html


# ---------------------------------------------------------------------------
# render_html — Chinese action labels displayed correctly
# ---------------------------------------------------------------------------


def test_render_html_buy_displays_chinese_label():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: BUY")
    html = render_html(data)
    assert "买入" in html


def test_render_html_sell_displays_chinese_label():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: SELL")
    html = render_html(data)
    assert "卖出" in html


def test_render_html_hold_displays_chinese_label():
    data = _minimal_data("FINAL TRANSACTION PROPOSAL: HOLD")
    html = render_html(data)
    assert "持有" in html
