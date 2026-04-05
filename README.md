# TradingAgents — Livermore Fork

Multi-agent LLM financial trading framework with Chinese localization and Z.AI GLM support.

Fork of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) ([paper](https://arxiv.org/abs/2412.20138)).

## What It Does

Deploys specialized LLM agents that collaboratively analyze a stock and produce a trading decision (BUY / SELL / HOLD / OVERWEIGHT / UNDERWEIGHT). The agents mirror a real trading firm:

```
Analyst Team (4 agents, parallel)
  ├── Fundamentals Analyst    → company financials
  ├── Market/Technical Analyst → MACD, RSI, Bollinger, etc.
  ├── News Analyst            → macro events, earnings
  └── Sentiment Analyst       → social media mood
          │
          ▼
Researcher Team (debate loop)
  ├── Bull Researcher (看多分析师)
  └── Bear Researcher (看空分析师)
          │  ← max_debate_rounds iterations
          ▼
Research Manager → synthesizes debate into investment plan
          │
          ▼
Trader Agent → drafts transaction proposal
          │
          ▼
Risk Management Team (debate loop)
  ├── Aggressive Debator (激进分析师)
  ├── Conservative Debator (保守分析师)
  └── Neutral Debator (中性分析师)
          │  ← max_risk_discuss_rounds iterations
          ▼
Portfolio Manager → final decision (BUY/SELL/HOLD/OVERWEIGHT/UNDERWEIGHT)
```

## Livermore Fork Differences

| Feature | Upstream | This Fork |
|---------|----------|-----------|
| LLM Provider | OpenAI default | Z.AI GLM (Coding API) |
| Output Language | English | Chinese (`output_language: "Chinese"`) |
| Agent Labels | `"Bull Analyst"` | `"看多分析师"` (Chinese) |
| Report Theme | Default | Light theme HTML |
| CI | None | GitHub Actions (pytest + ruff + BDD) |
| Test Coverage | ~6 tests | 559 tests, 69% coverage |

## Project Structure

```
tradingagents/
├── agents/
│   ├── analysts/           # 4 analyst agents (fundamentals, market, news, social)
│   ├── researchers/        # bull_researcher.py, bear_researcher.py
│   ├── managers/           # research_manager.py, portfolio_manager.py
│   ├── risk_mgmt/          # aggressive/conservative/neutral_debator.py
│   ├── trader/             # trader.py — final transaction proposal
│   └── utils/
│       ├── agent_utils.py  # get_language_instruction(), build_instrument_context()
│       ├── agent_states.py # LangGraph TypedDict state definitions
│       └── memory.py       # BM25-based agent memory (FinancialSituationMemory)
├── graph/
│   ├── trading_graph.py    # TradingAgentsGraph — main entry point
│   ├── setup.py            # LangGraph node/edge wiring
│   ├── conditional_logic.py # Debate/risk routing (CN/EN label-aware)
│   ├── signal_processing.py # Final signal rating
│   ├── propagation.py      # Forward propagation + backtesting
│   └── reflection.py       # Post-trade reflection → memory updates
├── llm_clients/
│   ├── factory.py          # create_llm_client(provider, model, ...)
│   ├── openai_client.py    # OpenAI/ZAI/XAI/Ollama/OpenRouter
│   ├── anthropic_client.py # Anthropic Claude
│   ├── google_client.py    # Google Gemini
│   ├── base_client.py      # Abstract base
│   ├── model_catalog.py    # Known models per provider
│   └── validators.py       # Model name validation
├── dataflows/
│   ├── interface.py        # Vendor dispatch (yfinance ↔ alpha_vantage)
│   ├── config.py           # Runtime config (get_config/set_config)
│   ├── y_finance.py        # yfinance data retrieval
│   ├── yfinance_news.py    # yfinance news retrieval
│   ├── stockstats_utils.py # Technical indicator computation
│   └── alpha_vantage*.py   # Alpha Vantage alternative vendor
└── default_config.py       # DEFAULT_CONFIG dict

cli/                        # Interactive CLI (Typer + Rich)
tests/                      # 559 tests (pytest + pytest-bdd)
.github/workflows/          # CI: test.yml, lint.yml, bdd.yml
```

## Installation

```bash
git clone https://github.com/frankyxhl/TradingAgents.git
cd TradingAgents
git checkout livermore

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

```python
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "zai"           # openai | zai | anthropic | google | xai | openrouter | ollama
config["deep_think_llm"] = "glm-5-turbo" # Model for complex reasoning
config["quick_think_llm"] = "glm-5-turbo" # Model for quick tasks
config["output_language"] = "Chinese"     # English | Chinese | any language
config["max_debate_rounds"] = 1           # Bull/Bear debate iterations
config["max_risk_discuss_rounds"] = 1     # Risk team debate iterations
```

### Environment Variables

| Variable | Provider | Required |
|----------|----------|----------|
| `ZAI_API_KEY` | Z.AI GLM | For this fork |
| `OPENAI_API_KEY` | OpenAI | If using OpenAI |
| `GOOGLE_API_KEY` | Google Gemini | If using Google |
| `ANTHROPIC_API_KEY` | Anthropic Claude | If using Anthropic |
| `XAI_API_KEY` | xAI Grok | If using xAI |
| `OPENROUTER_API_KEY` | OpenRouter | If using OpenRouter |

Set in `.env` file or export directly.

## Usage

### Python API

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv

load_dotenv()

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "zai"
config["deep_think_llm"] = "glm-5-turbo"
config["quick_think_llm"] = "glm-5-turbo"
config["output_language"] = "Chinese"

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("6861.T", "2026-04-04")  # Keyence, Tokyo
print(decision)  # "UNDERWEIGHT", "BUY", "SELL", "HOLD", or "OVERWEIGHT"
```

### CLI

```bash
tradingagents          # Interactive mode
python -m cli.main     # Alternative
```

### Supported Ticker Formats

| Market | Format | Example |
|--------|--------|---------|
| US | `SYMBOL` | `AAPL`, `NVDA` |
| Japan | `CODE.T` | `6861.T` (Keyence) |
| Hong Kong | `CODE.HK` | `2097.HK` |
| Toronto | `SYMBOL.TO` | `RY.TO` |
| London | `SYMBOL.L` | `SHEL.L` |

## Key Concepts

### LangGraph State Flow

The framework uses LangGraph to orchestrate agent execution. State is a TypedDict (`AgentState` in `agent_states.py`) passed between nodes:

```python
# Key state fields:
{
    "company_of_interest": "6861.T",
    "market_report": "...",           # From Market Analyst
    "sentiment_report": "...",        # From Sentiment Analyst
    "news_report": "...",             # From News Analyst
    "fundamentals_report": "...",     # From Fundamentals Analyst
    "investment_debate_state": {      # Bull/Bear debate
        "history": "...",
        "bull_history": "...",
        "bear_history": "...",
        "count": 0,
        "judge_decision": "...",      # Research Manager's synthesis
        "investment_plan": "...",
    },
    "risk_debate_state": {            # Risk team debate
        "history": "...",
        "aggressive_history": "...",
        "conservative_history": "...",
        "neutral_history": "...",
        "count": 0,
        "final_trade_decision": "...", # Portfolio Manager's final call
    },
    "trader_investment_plan": "...",   # Trader's proposal
}
```

### Conditional Routing (conditional_logic.py)

LangGraph routes between debate nodes using `startswith()` on the `latest_speaker` field. This is **label-sensitive** — Chinese labels like `"看多分析师"` must be handled alongside English `"Bull"`:

```python
# Bull speaker → route to Bear next
if speaker.startswith("Bull") or speaker.startswith("看多"):
    return "Bear Researcher"
```

### Data Vendor System (dataflows/)

Data retrieval is abstracted through a vendor dispatch system:

```
get_stock_data("AAPL", ...)
    → interface.route_to_vendor("get_stock_data", ...)
        → config says vendor = "yfinance"
            → y_finance.get_YFin_data_online(...)
        → if rate limited, fallback to alpha_vantage
```

### Agent Memory (BM25)

Each agent has a `FinancialSituationMemory` that stores past situations and recommendations. On new analysis, BM25 lexical similarity retrieves the most relevant past experiences to inject into the prompt.

## Testing

```bash
# Full test suite (559 tests, coverage gate 65%)
.venv/bin/python -m pytest tests/

# Lint
.venv/bin/ruff check tests/ tradingagents/ cli/

# BDD scenarios (provider routing, i18n, graph routing, e2e)
.venv/bin/python -m pytest tests/test_bdd_scenarios.py -v -o "addopts=" --no-cov
```

CI runs automatically on push/PR to `livermore` via GitHub Actions.

## Citation

Based on [TradingAgents](https://arxiv.org/abs/2412.20138) by Tauric Research:

```bibtex
@misc{xiao2025tradingagents,
    title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
    author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
    year={2025},
    eprint={2412.20138},
    archivePrefix={arXiv},
    primaryClass={q-fin.TR},
}
```
