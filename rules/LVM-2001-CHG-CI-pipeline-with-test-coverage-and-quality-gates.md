# CHG-2001: CI pipeline with test coverage and quality gates

**Applies to:** LVM project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Proposed
**Date:** 2026-04-04
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Depends on:** LVM-2000 (tests must exist before CI runs them)

---

## What

Set up GitHub Actions CI pipeline on the `livermore` branch with automated test execution, coverage reporting, and quality gates.

### Current State

| Item | Status |
|------|--------|
| `.github/workflows/` | Not exists |
| CI/CD | None |
| Test execution | Manual only (`python -m pytest tests/`) |
| Coverage enforcement | None |
| Lint/format checks | None |

## Why

Without CI, test regressions are only caught when someone remembers to run tests manually. The 2026-04-04 `conditional_logic.py` bug went live because there were no tests, but even after CHG-2000 adds tests, they're worthless if nobody runs them. CI makes the safety net automatic.

## Impact Analysis

- **Systems affected:** `.github/workflows/` (new), `pyproject.toml` (tool config)
- **Rollback plan:** Delete workflow files, CI stops running
- **Risk:** Low — CI is additive, no production code changes
- **Cost:** GitHub Actions free tier (2,000 mins/month for private repos, unlimited for public)

## Implementation Plan

### Phase 1: Basic CI — Unit Tests + Coverage

**File:** `.github/workflows/test.yml`

**Trigger:** Push/PR to `livermore`

```
Pipeline:
  Python: 3.13
  Steps:
    1. Checkout
    2. Install uv
    3. Create venv + install deps (uv pip install ".[dev]")
    4. Run pytest with coverage
    5. Upload coverage report
    6. Fail if coverage < threshold
```

| Gate | Threshold | Rationale |
|------|-----------|-----------|
| Tests pass | 100% | No broken tests allowed |
| Coverage (initial) | 50% | After CHG-2000 Phase 1 |
| Coverage (raise to) | 65% | After CHG-2000 Phase 2 |
| Coverage (long-term) | 75% | Sustainable target |

### Phase 2: Lint + Format

**Added to same workflow or separate job:**

| Tool | Purpose | Config |
|------|---------|--------|
| `ruff check` | Linting | `[tool.ruff]` in pyproject.toml |
| `ruff format --check` | Code style enforcement | Fail on unformatted code |

### Phase 3: BDD Tests (Behavioral)

**File:** `.github/workflows/bdd.yml`

**Trigger:** Push/PR to `livermore` (separate job, longer runtime)

| Test Scenario | What it verifies |
|---------------|------------------|
| Provider routing | "Given provider zai, when creating client, then use Z.AI Coding API endpoint" |
| Chinese localization | "Given output_language=Chinese, when agent runs, then labels are in Chinese" |
| Report rendering | "Given a JSON report, when rendered, then HTML contains no English labels" |
| Graph routing | "Given a Chinese debate response, when routing, then next node is Bear Researcher" |
| End-to-end (mock) | Full pipeline with mocked LLM responses, verify decision format |

**Note:** True E2E tests (hitting real LLM APIs) are NOT in CI — too slow, too expensive, non-deterministic. Those stay as manual `python test_zai.py`.

### Phase 4: Coverage Badge + PR Checks

| Item | Detail |
|------|--------|
| Coverage badge | Add to README via codecov or coverage-badge action |
| PR required checks | Tests + lint must pass before merge to livermore |
| Coverage diff | PR must not decrease coverage |

## pyproject.toml Changes

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=tradingagents --cov=cli --cov-report=term-missing"

[tool.coverage.run]
source = ["tradingagents", "cli"]

[tool.coverage.report]
fail_under = 50
show_missing = true

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I"]

[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-cov>=7.0",
    "ruff>=0.11",
]
```

## Execution Order

CHG-2000 and CHG-2001 phases interleave:

```
CHG-2000 Phase 1 (write tests, 33% → 54%)
    ▼
CHG-2001 Phase 1 (CI runs tests, coverage gate = 50%)
    ▼
CHG-2001 Phase 2 (add ruff lint + format)
    ▼
CHG-2000 Phase 2 (more tests, 54% → 66%)
    ▼
CHG-2001 Phase 3 (BDD tests in CI)
    ▼
CHG-2000 Phase 3 (data layer tests, → 70%+)
    ▼
CHG-2001 Phase 4 (badge, PR checks, coverage diff)
    ▼
Raise coverage gate to 75%
```

## Approval

- [ ] Approved by: —

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version with 4-phase plan | Frank + Claude Code |
