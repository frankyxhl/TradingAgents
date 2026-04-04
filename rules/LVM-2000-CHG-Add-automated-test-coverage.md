# CHG-2000: Add automated test coverage

**Applies to:** LVM project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Proposed
**Date:** 2026-04-04
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal

---

## What

Add automated test suite to improve code quality and prevent regressions.

### Current State (baseline 2026-04-04)

| Metric | Value |
|--------|-------|
| Test files | 3 |
| Test cases | 6 (+31 subtests) |
| Total statements | 1,332 |
| Covered | 444 (33%) |
| Uncovered | 888 (67%) |

### Coverage by Module (current)

| Module | Coverage | Stmts/Miss | Notes |
|--------|----------|------------|-------|
| `llm_clients/` | 37-89% | 146/62 | Has model validation + API key tests |
| `cli/` | 27% | 78/57 | Only ticker normalize tested |
| `agents/analysts/` | 26% | 92/68 | Only import-level coverage |
| `agents/researchers/` | 19% | 52/42 | Zero tests |
| `agents/risk_mgmt/` | 18-22% | 67/54 | Zero tests |
| `agents/managers/` | 8-18% | 46/40 | Zero tests |
| `agents/trader/` | 15% | 33/28 | Zero tests |
| `dataflows/` | 3-60% | 441/389 | Zero tests, heaviest uncovered |
| `graph/` | 0% | ~40/40 | Not even imported by tests |
| `render_report.py` | N/A | ~120/120 | New file, no tests |

## Why

The `conditional_logic.py` routing bug on 2026-04-04 (Chinese label prefix `"看多分析师"` broke `startswith("Bull")` check in LangGraph routing) would have been caught by a 5-line unit test. As we continue customizing the Livermore fork (i18n, new providers, theme), automated tests are essential to prevent similar regressions.

## Impact Analysis

- **Systems affected:** `tests/` directory (new files), `pyproject.toml` (pytest config)
- **Rollback plan:** Delete new test files, revert pyproject.toml
- **Risk:** Low — adding tests only, no production code changes

## Implementation Plan

### Phase 1: Pure Logic + Light Mocks → target 54%

No LLM calls, no external APIs. Pure unit tests.

| # | File | Test Cases | Uncovered Lines | Priority |
|---|------|------------|-----------------|----------|
| 1 | `graph/conditional_logic.py` | debate routing CN/EN, risk routing CN/EN, round limits | ~30 | **Critical** — 2026-04-04 bug |
| 2 | `graph/signal_processing.py` | signal parsing (BUY/SELL/HOLD) | ~10 | High |
| 3 | `render_report.py` | action extraction CN/EN, md_to_html, flatten() | ~120 | High |
| 4 | `llm_clients/factory.py` | provider→client routing (openai, zai, xai, anthropic, google, ollama) | 10 | High |
| 5 | `llm_clients/openai_client.py` | provider config lookup, base URL, API key env var | 22 | Medium |
| 6 | `llm_clients/anthropic_client.py` | client creation with mock | 11 | Medium |
| 7 | `agents/utils/agent_utils.py` | `get_language_instruction()` with/without Chinese, `build_instrument_context()` | 11 | High |
| 8 | `dataflows/config.py` | config get/set, vendor resolution | 6 | Low |
| 9 | `dataflows/interface.py` | vendor dispatch, tool→vendor mapping | 30 | Medium |

**Estimated new coverage: 33% → 54% (+271 lines)**

### Phase 2: Agent Node Tests (Mock LLM) → target 66%

Mock `llm.invoke()` to test prompt construction, state updates, and label prefixes.

| # | File | Test Cases | Uncovered Lines |
|---|------|------------|-----------------|
| 10 | `agents/researchers/bull_researcher.py` | CN/EN label prefix, state update format, memory integration | 21 |
| 11 | `agents/researchers/bear_researcher.py` | Same as above | 21 |
| 12 | `agents/risk_mgmt/aggressive_debator.py` | CN/EN label, latest_speaker value, state update | 18 |
| 13 | `agents/risk_mgmt/conservative_debator.py` | Same | 18 |
| 14 | `agents/risk_mgmt/neutral_debator.py` | Same | 18 |
| 15 | `agents/trader/trader.py` | CN/EN prompt selection, conclusion format | 28 |
| 16 | `agents/managers/research_manager.py` | Language instruction injection | 18 |
| 17 | `agents/managers/portfolio_manager.py` | CN/EN prompt, rating scale | 22 |

**Estimated new coverage: 54% → 66% (+164 lines)**

### Phase 3: External Data Layer (Heavy Mocks) → target 70%+

Mock yfinance/requests for data retrieval tests. Higher effort, lower priority.

| # | File | Test Cases | Uncovered Lines |
|---|------|------------|-----------------|
| 18 | `dataflows/y_finance.py` | Stock data parsing, indicator window, mock yfinance | 136 |
| 19 | `dataflows/yfinance_news.py` | News retrieval, error handling | 91 |
| 20 | `dataflows/stockstats_utils.py` | Indicator calculation | 47 |
| 21 | `agents/utils/memory.py` | Memory store/retrieve with mock Redis | 41 |

**Estimated new coverage: 66% → 70%+ (selective, highest-value lines)**

### Infrastructure

| Item | Detail |
|------|--------|
| pytest config | `[tool.pytest.ini_options]` in `pyproject.toml` |
| Coverage config | `[tool.coverage]` minimum threshold |
| Test deps | `pytest`, `pytest-cov` added to dev dependencies |
| CI (optional) | GitHub Actions on push to `livermore` |

### Coverage Targets

| Milestone | Coverage | Tests | Effort |
|-----------|----------|-------|--------|
| Baseline (current) | 33% | 6 | — |
| Phase 1 complete | 54% | ~30 | 1 session |
| Phase 2 complete | 66% | ~50 | 1 session |
| Phase 3 complete | 70%+ | ~60 | 1-2 sessions |
| Long-term goal | 80% | ~80 | Incremental |

## Approval

- [ ] Approved by: —

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version with 3-phase plan | Frank + Claude Code |
| 2026-04-04 | Detailed breakdown: per-file test cases, line counts, coverage targets by phase | Frank + Claude Code |
