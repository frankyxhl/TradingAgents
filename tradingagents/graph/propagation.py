# TradingAgents/graph/propagation.py

from typing import Any, Dict, List, Optional

from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    # Cache resolved company names to avoid repeated yfinance calls
    _company_name_cache: Dict[str, str] = {}

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def _resolve_company_name(self, ticker: str) -> str:
        """Resolve human-readable company name from ticker via yfinance.

        Results are cached per ticker to avoid repeated API calls
        in multi-date evaluations.
        """
        if ticker in self._company_name_cache:
            return self._company_name_cache[ticker]

        resolved_name = ticker  # fallback
        try:
            import yfinance as yf

            from tradingagents.dataflows.y_finance import yf_retry

            info = yf_retry(lambda: yf.Ticker(ticker).info)
            resolved_name = info.get("longName") or info.get("shortName") or ticker
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to resolve company name for {ticker}, using ticker as fallback: {exc}",
                exc_info=True,
            )

        self._company_name_cache[ticker] = resolved_name
        return resolved_name

    def create_initial_state(self, company_name: str, trade_date: str) -> Dict[str, Any]:
        """Create the initial state for the agent graph."""
        resolved_name = self._resolve_company_name(company_name)

        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "resolved_company_name": resolved_name,
            "trade_date": str(trade_date),
            "investment_debate_state": InvestDebateState(
                {
                    "bull_history": "",
                    "bear_history": "",
                    "history": "",
                    "current_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "aggressive_history": "",
                    "conservative_history": "",
                    "neutral_history": "",
                    "history": "",
                    "latest_speaker": "",
                    "current_aggressive_response": "",
                    "current_conservative_response": "",
                    "current_neutral_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
        }

    def get_graph_args(self, callbacks: Optional[List] = None) -> Dict[str, Any]:
        """Get arguments for the graph invocation.

        Args:
            callbacks: Optional list of callback handlers for tool execution tracking.
                       Note: LLM callbacks are handled separately via LLM constructor.
        """
        config = {"recursion_limit": self.max_recur_limit}
        if callbacks:
            config["callbacks"] = callbacks
        return {
            "stream_mode": "values",
            "config": config,
        }
