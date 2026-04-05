#!/usr/bin/env python3
"""TradingAgents CLI analysis script.

Usage:
    python scripts/analyze.py --ticker MSFT
    python scripts/analyze.py --ticker 6861.T --date 2026-04-04 --language Chinese
    python scripts/analyze.py --ticker MSFT --output pdf
    python scripts/analyze.py --ticker MSFT --output both
"""

import argparse
import sys
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Run TradingAgents stock analysis")
    parser.add_argument(
        "--ticker",
        required=True,
        help="Stock ticker (e.g., MSFT, 6861.T, 2097.HK)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Analysis date (YYYY-MM-DD). Default: yesterday",
    )
    parser.add_argument(
        "--language",
        default="Chinese",
        help="Output language (default: Chinese)",
    )
    parser.add_argument(
        "--provider",
        default="zai",
        help="LLM provider (default: zai)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model (auto-selected per provider if omitted)",
    )
    parser.add_argument(
        "--output",
        default="text",
        choices=["text", "html", "pdf", "both"],
        help="Output format",
    )
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()

    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    if args.date is None:
        from datetime import timedelta

        args.date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Error: invalid date format '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)

    args.provider = args.provider.lower()

    # Default models per provider
    _DEFAULT_MODELS = {
        "zai": "glm-5-turbo",
        "openai": "gpt-5.4-mini",
        "anthropic": "claude-sonnet-4-6",
        "google": "gemini-2.5-flash",
        "xai": "grok-4-fast-non-reasoning",
        "openrouter": "gpt-5.4-mini",
        "ollama": "llama3",
    }
    model = args.model or _DEFAULT_MODELS.get(args.provider, "gpt-5.4-mini")

    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = args.provider
    config["deep_think_llm"] = model
    config["quick_think_llm"] = model
    # Clear backend_url so each provider uses its own default endpoint
    config["backend_url"] = None
    config["output_language"] = args.language
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1

    print(f"Analyzing {args.ticker} on {args.date}...")
    ta = TradingAgentsGraph(debug=True, config=config)
    state, decision = ta.propagate(args.ticker, args.date)

    print(f"\nDecision: {decision}")

    if args.output in ("html", "both"):
        from tradingagents.render_report import render_html

        html = render_html(state)
        html_path = f"{args.ticker}_{args.date}_report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML report: {html_path}")

    if args.output in ("pdf", "both"):
        from tradingagents.render_report import render_pdf

        pdf_path = render_pdf(state)
        print(f"PDF report: {pdf_path}")


if __name__ == "__main__":
    main()
