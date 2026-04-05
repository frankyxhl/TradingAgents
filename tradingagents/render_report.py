"""Render TradingAgents JSON report to HTML."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


def md_to_html(text: str) -> str:
    """Minimal markdown to HTML conversion."""
    lines = text.split("\n")
    html_lines = []
    in_table = False
    in_list = False
    table_header_done = False

    for line in lines:
        stripped = line.strip()

        # Horizontal rule
        if stripped in ("---", "***", "___") and not in_table:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<hr>")
            continue

        # Table rows
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # Skip separator rows like |---|---|
            if all(re.match(r"^[-:]+$", c) for c in cells):
                table_header_done = True
                continue
            if not in_table:
                html_lines.append('<div class="table-wrap"><table>')
                in_table = True
                table_header_done = False
            tag = "th" if not table_header_done else "td"
            row = "".join(f"<{tag}>{inline_md(c)}</{tag}>" for c in cells)
            html_lines.append(f"<tr>{row}</tr>")
            continue
        elif in_table:
            html_lines.append("</table></div>")
            in_table = False
            table_header_done = False

        # Headers
        m = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if m:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            level = len(m.group(1))
            html_lines.append(f"<h{level}>{inline_md(m.group(2))}</h{level}>")
            continue

        # Unordered list
        m = re.match(r"^[-*]\s+(.*)", stripped)
        if m:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline_md(m.group(1))}</li>")
            continue

        # Numbered list
        m = re.match(r"^\d+\.\s+(.*)", stripped)
        if m:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline_md(m.group(1))}</li>")
            continue

        if in_list and stripped == "":
            html_lines.append("</ul>")
            in_list = False

        # Paragraph
        if stripped:
            html_lines.append(f"<p>{inline_md(stripped)}</p>")

    if in_table:
        html_lines.append("</table></div>")
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def inline_md(text: str) -> str:
    """Convert inline markdown (bold, italic, code, emoji)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def render_html(data: dict) -> str:
    """Build full HTML report from parsed JSON."""
    date = data["trade_date"]
    ticker = data["company_of_interest"]
    decision = data.get("final_trade_decision", "N/A")

    # Extract the final action (English or Chinese format)
    action = "N/A"
    # Try English format first
    m = re.search(r"FINAL TRANSACTION PROPOSAL:\s*\*?\*?(\w+)", decision)
    if m:
        action = m.group(1).upper()
    else:
        # Try Chinese format: 最终交易建议：**卖出**
        m = re.search(r"最终交易建议[：:]\s*\*?\*?(买入|卖出|持有|增持|减持)", decision)
        if m:
            action = {
                "买入": "BUY",
                "卖出": "SELL",
                "持有": "HOLD",
                "增持": "OVERWEIGHT",
                "减持": "UNDERWEIGHT",
            }[m.group(1)]
        else:
            # Fallback: scan tail for keywords
            tail = decision[-300:]
            cn_map = [
                ("强力买入", "BUY"),
                ("建议减持", "UNDERWEIGHT"),
                ("建议买入", "BUY"),
                ("建议卖出", "SELL"),
                ("建议持有", "HOLD"),
                ("减持", "UNDERWEIGHT"),
                ("增持", "OVERWEIGHT"),
                ("买入", "BUY"),
                ("卖出", "SELL"),
                ("持有", "HOLD"),
            ]
            for cn, en in cn_map:
                if cn in tail:
                    action = en
                    break
            else:
                for kw in ("SELL", "BUY", "HOLD", "UNDERWEIGHT", "OVERWEIGHT"):
                    if kw in tail.upper():
                        action = kw
                        break
    action_label = {
        "BUY": "买入",
        "SELL": "卖出",
        "HOLD": "持有",
        "STRONG": "强力买入",
        "UNDERWEIGHT": "减持",
        "OVERWEIGHT": "增持",
    }
    action_class = {
        "BUY": "buy",
        "SELL": "sell",
        "HOLD": "hold",
        "STRONG": "buy",
        "UNDERWEIGHT": "sell",
        "OVERWEIGHT": "buy",
    }.get(action.upper(), "hold")
    action_display = action_label.get(action.upper(), action)

    sections = [
        ("技术分析", data.get("market_report", "")),
        ("情绪分析", data.get("sentiment_report", "")),
        ("新闻分析", data.get("news_report", "")),
        ("基本面分析", data.get("fundamentals_report", "")),
    ]

    debate = data.get("investment_debate_state", {})
    risk = data.get("risk_debate_state", {})

    def flatten(val):
        """Ensure value is a single string, joining lists if needed."""
        if isinstance(val, list):
            return "\n\n".join(str(m) for m in val)
        return str(val)

    debate_sections = []
    if debate.get("bull_history"):
        debate_sections.append(("看多观点", flatten(debate["bull_history"])))
    if debate.get("bear_history"):
        debate_sections.append(("看空观点", flatten(debate["bear_history"])))
    if debate.get("judge_decision"):
        debate_sections.append(("裁判决定", flatten(debate["judge_decision"])))

    risk_sections = []
    if risk.get("aggressive_history"):
        risk_sections.append(("激进观点", flatten(risk["aggressive_history"])))
    if risk.get("conservative_history"):
        risk_sections.append(("保守观点", flatten(risk["conservative_history"])))
    if risk.get("neutral_history"):
        risk_sections.append(("中性观点", flatten(risk["neutral_history"])))
    if risk.get("judge_decision"):
        risk_sections.append(("风控委员会决定", flatten(risk["judge_decision"])))

    trader_plan = data.get("trader_investment_decision", "")

    nav_items = ""
    body_sections = ""

    # Analyst reports
    for title, content in sections:
        sid = title.lower().replace(" ", "-")
        nav_items += f'<a href="#{sid}">{title}</a>\n'
        body_sections += f'''
        <section id="{sid}">
            <h2>{title}</h2>
            <div class="report-content">{md_to_html(content)}</div>
        </section>'''

    # Investment Debate
    if debate_sections:
        nav_items += '<a href="#debate">投资辩论</a>\n'
        debate_html = ""
        for title, content in debate_sections:
            cls = "bull" if "看多" in title else "bear" if "看空" in title else "judge"
            debate_html += (
                f'<div class="debate-card {cls}"><h3>{title}</h3>{md_to_html(content)}</div>'
            )
        body_sections += f"""
        <section id="debate">
            <h2>投资辩论</h2>
            <div class="debate-grid">{debate_html}</div>
        </section>"""

    # Trader Decision
    if trader_plan:
        nav_items += '<a href="#trader">交易员决策</a>\n'
        body_sections += f"""
        <section id="trader">
            <h2>交易员决策</h2>
            <div class="report-content">{md_to_html(str(trader_plan))}</div>
        </section>"""

    # Risk Assessment
    if risk_sections:
        nav_items += '<a href="#risk">风险评估</a>\n'
        risk_html = ""
        for title, content in risk_sections:
            cls = (
                "aggressive"
                if "激进" in title
                else "conservative"
                if "保守" in title
                else "neutral"
            )
            risk_html += (
                f'<div class="debate-card {cls}"><h3>{title}</h3>{md_to_html(content)}</div>'
            )
        body_sections += f"""
        <section id="risk">
            <h2>风险评估</h2>
            <div class="debate-grid">{risk_html}</div>
        </section>"""

    # Final Decision
    nav_items += '<a href="#decision">最终决策</a>\n'
    body_sections += f"""
    <section id="decision">
        <h2>最终决策</h2>
        <div class="report-content">{md_to_html(decision)}</div>
    </section>"""

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{ticker} 投资分析报告 - {date}</title>
<style>
:root {{
    --bg: #f8f9fa; --surface: #ffffff; --border: #e1e4e8;
    --text: #24292f; --text-muted: #656d76; --accent: #0969da;
    --green: #1a7f37; --red: #cf222e; --yellow: #9a6700;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.7; }}
.header {{ background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 2rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.header h1 {{ font-size: 2.2rem; margin-bottom: 0.5rem; color: var(--text); }}
.header .date {{ color: var(--text-muted); font-size: 1rem; }}
.badge {{ display: inline-block; padding: 0.4rem 1.5rem; border-radius: 2rem;
    font-weight: 700; font-size: 1.3rem; margin-top: 1rem; letter-spacing: 0.05em; }}
.badge.buy {{ background: #dafbe1; color: var(--green); border: 2px solid var(--green); }}
.badge.sell {{ background: #ffebe9; color: var(--red); border: 2px solid var(--red); }}
.badge.hold {{ background: #fff8c5; color: var(--yellow); border: 2px solid var(--yellow); }}
nav {{ background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 0.8rem 2rem; display: flex; gap: 0.5rem; flex-wrap: wrap;
    position: sticky; top: 0; z-index: 10; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
nav a {{ color: var(--text-muted); text-decoration: none; padding: 0.4rem 0.8rem;
    border-radius: 0.4rem; font-size: 0.85rem; transition: all 0.2s; }}
nav a:hover {{ background: #eef1f4; color: var(--text); }}
.container {{ max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; }}
section {{ background: var(--surface); border: 1px solid var(--border);
    border-radius: 0.75rem; padding: 2rem; margin-bottom: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
h2 {{ color: var(--accent); font-size: 1.4rem; margin-bottom: 1.2rem;
    padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }}
h3 {{ color: var(--text); font-size: 1.1rem; margin: 1rem 0 0.5rem; }}
h4 {{ color: var(--text-muted); margin: 0.8rem 0 0.4rem; }}
p {{ margin-bottom: 0.8rem; }}
ul {{ padding-left: 1.5rem; margin-bottom: 0.8rem; }}
li {{ margin-bottom: 0.3rem; }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 1.2rem 0; }}
strong {{ color: #1b1f24; }}
code {{ background: #eff1f3; padding: 0.15rem 0.4rem;
    border-radius: 0.25rem; font-size: 0.9em; color: #cf222e; }}
.table-wrap {{ overflow-x: auto; margin: 1rem 0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
th, td {{ padding: 0.5rem 0.8rem; border: 1px solid var(--border); text-align: left; }}
th {{ background: #f0f6ff; color: var(--accent); font-weight: 600; }}
tr:nth-child(even) td {{ background: #f8f9fa; }}
.debate-grid {{ display: grid; grid-template-columns: 1fr; gap: 1rem; }}
.debate-card {{ border: 1px solid var(--border); border-radius: 0.5rem; padding: 1.2rem;
    border-left: 4px solid var(--border); background: var(--surface); }}
.debate-card.bull {{ border-left-color: var(--green); background: #f6fef8; }}
.debate-card.bear {{ border-left-color: var(--red); background: #fffbfa; }}
.debate-card.judge {{ border-left-color: var(--accent); background: #f6f8ff; }}
.debate-card.aggressive {{ border-left-color: var(--red); background: #fffbfa; }}
.debate-card.conservative {{ border-left-color: var(--green); background: #f6fef8; }}
.debate-card.neutral {{ border-left-color: var(--yellow); background: #fffef5; }}
.debate-card h3 {{ margin-top: 0; }}
footer {{ text-align: center; color: var(--text-muted); font-size: 0.8rem;
    padding: 2rem; border-top: 1px solid var(--border); }}
@media (max-width: 600px) {{
    .header h1 {{ font-size: 1.5rem; }}
    section {{ padding: 1.2rem; }}
    nav {{ padding: 0.5rem 1rem; }}
}}
</style>
</head>
<body>
<div class="header">
    <h1>{ticker} 投资分析报告</h1>
    <div class="date">分析日期：{date}</div>
    <div class="badge {action_class}">{action_display}</div>
</div>
<nav>{nav_items}</nav>
<div class="container">
{body_sections}
</div>
<footer>由 TradingAgents + GLM-5-Turbo 生成 | {generated}</footer>
</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        # Find most recent report
        reports = sorted(Path("eval_results").rglob("full_states_log_*.json"))
        if not reports:
            print("No reports found. Pass a JSON file path as argument.")
            sys.exit(1)
        json_path = reports[-1]
    else:
        json_path = Path(sys.argv[1])

    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)

    # JSON is keyed by date
    date_key = list(raw.keys())[0]
    data = raw[date_key]

    html = render_html(data)
    out_path = json_path.with_suffix(".html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Report saved to: {out_path}")


if __name__ == "__main__":
    main()
