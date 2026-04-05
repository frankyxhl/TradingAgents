# SOP-1001: Pre-Push CI Gate

**Applies to:** LVM project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Active

---

## What Is It?

A mandatory local verification gate that must pass before any `git push` to remote. Replicates the full GitHub Actions CI pipeline locally to catch failures before they waste CI minutes and review time.

## Why

On 2026-04-04, code was pushed to PR frankyxhl/TradingAgents#1 without local CI verification. All 3 GitHub Actions workflows failed on the first run (missing `pytest-bdd` dependency, 99 ruff lint errors in tests, pyproject.toml `addopts` conflict with BDD). A second push was needed to fix, then a third for remaining issues. Local verification would have caught all problems before the first push.

---

## When to Use

- Before every `git push` to any remote branch
- Before creating a PR
- After fixing CI failures, before re-pushing

## When NOT to Use

- Local-only branches that will never be pushed
- When Frank explicitly waives the gate (e.g., "push it, I'll fix in CI")

---

## Steps

1. **Run unit tests + coverage gate**

```bash
.venv/bin/python -m pytest tests/
```

Pass criteria: all tests pass, coverage >= `fail_under` threshold in pyproject.toml (currently 65%).

2. **Run ruff lint on tests**

```bash
.venv/bin/ruff check tests/
```

Pass criteria: 0 errors.

3. **Run ruff format check on tests**

```bash
.venv/bin/ruff format --check tests/
```

Pass criteria: 0 files would be reformatted.

4. **Run BDD scenarios**

```bash
.venv/bin/python -m pytest tests/test_bdd_scenarios.py -v -o "addopts=" --no-cov
```

Pass criteria: all BDD scenarios pass.

5. **All 4 pass → push allowed**

```bash
git push origin <branch>
```

If ANY step fails: fix the issue, re-run ALL steps from step 1, then push.

---

## Quick Reference

One-liner to run all 4 checks sequentially (stops on first failure):

```bash
.venv/bin/python -m pytest tests/ \
  && .venv/bin/ruff check tests/ \
  && .venv/bin/ruff format --check tests/ \
  && .venv/bin/python -m pytest tests/test_bdd_scenarios.py -v -o "addopts=" --no-cov
```

---

## Updating This Gate

When CI configuration changes (new workflow, new tool, new threshold), this SOP must be updated to match. The local gate must always mirror the remote CI pipeline.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version — triggered by 3 consecutive CI failures on PR #1 | Claude Code |
