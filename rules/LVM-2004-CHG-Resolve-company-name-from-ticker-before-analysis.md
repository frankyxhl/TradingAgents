# CHG-2004: Resolve company name from ticker before analysis

**Applies to:** TradingAgents (Livermore fork)
**Last updated:** 2026-04-06
**Last reviewed:** 2026-04-06
**Status:** Proposed
**Date:** 2026-04-06
**Requested by:** Frank
**Priority:** High
**Change Type:** Normal

---

## What

Resolve the actual company name from the ticker symbol via yfinance before starting analysis, and inject it into all agent prompts so LLMs don't hallucinate wrong companies.

### Current State

```
propagate("9348.T", "2026-04-04")
    → state["company_of_interest"] = "9348.T"
    → build_instrument_context("9348.T") = "The instrument to analyze is 9348.T..."
    → GLM sees only "9348.T", guesses "ABC-Mart Holdings" ← WRONG (should be ispace)
```

### Target State

```
propagate("9348.T", "2026-04-04")
    → yf.Ticker("9348.T").info["longName"] = "ispace, inc."
    → state["resolved_company_name"] = "ispace, inc."
    → build_instrument_context("9348.T", "ispace, inc.")
      = "The instrument to analyze is ispace, inc. (9348.T)..."
    → GLM knows exactly which company it's analyzing ← CORRECT
```

## Why

On 2026-04-06, a real analysis of ispace (9348.T) produced a report with "ABC-Mart Holdings" in the sentiment section. GLM hallucinated the wrong company because it only received the ticker symbol `9348.T` without the company name. This is a critical accuracy issue — the entire analysis is invalidated when the LLM analyzes the wrong company.

## Impact Analysis

- **Systems affected:** 10 files (see Steps 1-4 for full list)
- **Rollback plan:** Revert all 10 files; agents go back to ticker-only context
- **Risk:** Low — additive context injection, no logic change. `build_instrument_context` signature is backward-compatible (new param has default `None`). yfinance `.info` call adds ~1-2s at startup but only once per analysis run.

## Implementation Plan

### Step 1: Add company name resolution in `propagation.py`

In `Propagator.create_initial_state()`, add yfinance lookup. Note: the existing parameter `company_name` is actually a ticker — we use `resolved_company_name` for the state key to avoid naming confusion.

```python
def create_initial_state(self, company_name: str, trade_date: str) -> Dict[str, Any]:
    # Resolve human-readable company name from ticker via yfinance
    resolved_name = company_name  # fallback to ticker
    try:
        import yfinance as yf
        info = yf.Ticker(company_name).info
        resolved_name = info.get("longName") or info.get("shortName") or company_name
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            f"Failed to resolve company name for {company_name}, using ticker as fallback"
        )

    return {
        "messages": [("human", company_name)],
        "company_of_interest": company_name,
        "resolved_company_name": resolved_name,  # ← NEW
        "trade_date": str(trade_date),
        ...
    }
```

### Step 2: Update `build_instrument_context()` in `agent_utils.py`

Accept optional company name and include it in the context:

```python
def build_instrument_context(ticker: str, company_name: str = None) -> str:
    name_str = f"{company_name} ({ticker})" if company_name else f"`{ticker}`"
    return (
        f"The instrument to analyze is {name_str}. "
        f"The company is {company_name or ticker}. "
        "Use the exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`)."
    )
```

### Step 3: Update all callers of `build_instrument_context`

Pass `state.get("resolved_company_name")` as second argument.

**Files that call `build_instrument_context` (verified by grep):**

| File | Line | Current call |
|------|------|-------------|
| `agents/analysts/fundamentals_analyst.py` | 21 | `build_instrument_context(state["company_of_interest"])` |
| `agents/analysts/market_analyst.py` | 19 | same |
| `agents/analysts/news_analyst.py` | 18 | same |
| `agents/analysts/social_media_analyst.py` | 17 | same |
| `agents/managers/research_manager.py` | 12 | same |
| `agents/managers/portfolio_manager.py` | 10 | same |
| `agents/trader/trader.py` | 14 | same |

Each becomes (for most files):
```python
build_instrument_context(state["company_of_interest"], state.get("resolved_company_name"))
```

Note: `trader.py` uses a local variable `company_name = state["company_of_interest"]`, so its call becomes:
```python
build_instrument_context(company_name, state.get("resolved_company_name"))
```

**Files that do NOT call `build_instrument_context` (no change needed):**
- `agents/researchers/bull_researcher.py` — receives company context indirectly via analyst reports
- `agents/researchers/bear_researcher.py` — same
- `agents/risk_mgmt/aggressive_debator.py` — receives context via trader decision
- `agents/risk_mgmt/conservative_debator.py` — same
- `agents/risk_mgmt/neutral_debator.py` — same

### Step 4: Update `AgentState` TypedDict

Add `resolved_company_name` as optional field to `agents/utils/agent_states.py`:

```python
resolved_company_name: Optional[str]
```

Using `Optional[str]` ensures backward compatibility — existing code that constructs partial states without this field won't break.

### Step 5: Tests

| Test | What it verifies |
|------|-----------------|
| `create_initial_state` returns `resolved_company_name` | Mock yfinance → state dict contains resolved name |
| yfinance failure fallback | Mock yfinance raises → `resolved_company_name` equals ticker |
| yfinance failure logs warning | Mock yfinance raises → warning logged |
| `build_instrument_context` with company name | Output contains both "ispace" and "9348.T" |
| `build_instrument_context` without company name | Backward compatible, output contains ticker |
| Existing `test_agent_utils.py` tests still pass | No regression from signature change |

### Step 6 (optional): Update `render_report.py`

Display `resolved_company_name` in report title if available:
```
ispace, inc. (9348.T) 投资分析报告
```
instead of:
```
9348.T 投资分析报告
```

## Approval

- [ ] Approved by: —

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-06 | Initial version — triggered by ispace/ABC-Mart misidentification incident | Frank + Claude Code |
| 2026-04-06 | R1 fix: correct Step 3 file list (analysts, not researchers), rename to resolved_company_name, add Optional typing, update rollback plan, add logging | Claude Code |
