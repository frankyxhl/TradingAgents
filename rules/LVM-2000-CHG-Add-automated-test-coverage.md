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

Add automated test suite to improve code quality and prevent regressions. Current state: 6 tests, 33% coverage. Core modules (agents, graph, dataflows) have near-zero coverage.

## Why

The conditional_logic.py routing bug on 2026-04-04 (Chinese label prefix broke LangGraph routing) would have been caught by a simple unit test. As we continue customizing the Livermore fork, automated tests are essential to prevent similar regressions.

## Impact Analysis

- **Systems affected:** `tests/` directory (new files), `pyproject.toml` (pytest config)
- **Rollback plan:** Delete new test files, revert pyproject.toml

## Implementation Plan

### Phase 1: High-value unit tests (priority)
1. `conditional_logic.py` — debate/risk routing with CN/EN prefixes
2. `llm_clients/factory.py` — provider routing (including zai)
3. `render_report.py` — action extraction (CN/EN formats)
4. `model_catalog.py` — zai models in catalog

### Phase 2: Data layer tests (mock-based)
5. `dataflows/interface.py` — vendor dispatch logic
6. `dataflows/y_finance.py` — data retrieval with mocked yfinance

### Phase 3: Integration tests
7. Agent prompt construction — verify `get_language_instruction()` injection
8. Graph setup — node names and edges consistency

### Target
- Phase 1 目标覆盖率：50%+
- Phase 1-3 完成后目标：65%+
- pytest config in pyproject.toml
- CI 可选（GitHub Actions）

## Approval

- [ ] Approved by: —

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version with 3-phase plan | Frank + Claude Code |
