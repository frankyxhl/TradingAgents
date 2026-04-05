# SOP-1002: Commit and Release Flow

**Applies to:** TradingAgents (Livermore fork)
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** Active
**Related:** LVM-1001 (Pre-Push CI Gate), COR-1502 (Branch Naming), COR-1606 (Workflow Selection)

---

## What Is It?

The mandatory end-to-end flow for getting code changes from local branch into `livermore`. Every change follows: branch → commit → local CI → push → PR → review → Frank merges.

---

## Why

On 2026-04-04, multiple pushes were needed because CI checks weren't run locally, branch naming didn't follow conventions, and review comments weren't addressed before pushing fixes. A standardized flow prevents these issues.

---

## When to Use

- After completing any code change (feature, fix, refactor, tests, docs)
- When ready to integrate work into `livermore`

## When NOT to Use

- Work-in-progress that isn't ready for integration yet
- Upstream sync (use LVM-1000 Upstream Sync Procedure instead)

---

## Flow

```
Work complete on livermore
     │
     ▼
Step 1: Create branch (COR-1502)
     │
     ▼
Step 2: Stage + Commit
     │
     ▼
Step 3: Local CI Gate (LVM-1001)
     │  ALL 4 checks must pass
     │  If fail → fix → re-run from Step 2
     ▼
Step 4: Push
     │
     ▼
Step 5: Create PR
     │
     ▼
Step 6: Review (Gemini + Codex)
     │  Score >= 9 → PASS
     │  Score < 9 → fix → re-push → re-review
     ▼
Step 7: Address PR comments
     │  Fix all review comments
     │  Reply with commit SHA
     │  Re-run LVM-1001 before push
     ▼
Step 8: Tell Frank — "PR #N is ready"
     │
     ▼         ← HARD STOP
Frank reviews and merges on GitHub
```

---

## Steps

### Step 1: Create branch

Per COR-1502 (Git Branch Naming):

```bash
git checkout livermore
git checkout -b <type>/<issue>-<short-description>
```

| Type | When |
|------|------|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `chore/` | CI, config, dependencies |
| `refactor/` | Code restructuring |
| `test/` | Adding tests only |
| `docs/` | Documentation only |

If no GitHub issue exists yet, create one first.

### Step 2: Stage and commit

```bash
git add <specific files>
git commit -m "<type>: <concise description>

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

Rules:
- Stage specific files, never `git add -A`
- Never commit `.env`, `.venv/`, `eval_results/`, `results/`
- Commit message: imperative mood, focus on "why" not "what"

### Step 3: Local CI Gate (LVM-1001)

**All 4 must pass before push:**

```bash
.venv/bin/python -m pytest tests/
.venv/bin/ruff check tests/ tradingagents/ cli/
.venv/bin/ruff format --check tests/ tradingagents/ cli/
.venv/bin/python -m pytest tests/test_bdd_scenarios.py -v -o "addopts=" --no-cov
```

If any fails: fix, amend or new commit, re-run ALL from step 1.

### Step 4: Push

```bash
git push -u origin <branch-name>
```

Only after LVM-1001 passes. No exceptions.

### Step 5: Create PR

```bash
gh pr create --base livermore --head <branch> \
  --title "<type>: <description>" \
  --body "$(cat <<'EOF'
## Summary
- <bullet points>

## Test plan
- [ ] All tests pass locally (LVM-1001)
- [ ] CI workflows pass
- [ ] <specific checks for this change>

Generated with Claude Code
EOF
)"
```

### Step 6: Review (Trinity)

Dispatch Gemini + Codex for review per COR-1603:

- Both reviewers must score >= 9/10
- If < 9: fix issues, re-push (with LVM-1001 gate), re-review
- Max 3 review rounds

### Step 7: Address PR comments

For each review comment (Copilot, Gemini, Codex, human):
1. Fix the issue in code
2. Run LVM-1001 locally
3. Commit and push
4. Reply to the comment with commit SHA

### Step 8: Notify Frank

When all checks green and all comments addressed:

> "PR #N is ready — please review and merge when you're ready."

**HARD STOP** — Claude never runs `gh pr merge`. Frank merges on GitHub.

---

## Forbidden Actions

| Action | Why |
|--------|-----|
| `gh pr merge` | Frank merges, never Claude |
| `git push` before LVM-1001 | Wastes CI runs |
| `git add -A` or `git add .` | May include secrets or generated files |
| `git push --force origin livermore` | Destroys shared history |
| Commit without branch | All work goes through PR, not direct to livermore |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-05 | Initial version — standardizes commit-to-merge flow for LVM project | Claude Code |
