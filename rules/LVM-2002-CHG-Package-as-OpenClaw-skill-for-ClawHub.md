# CHG-2002: Package as OpenClaw skill for ClawHub

**Applies to:** LVM project
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** Proposed
**Date:** 2026-04-05
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal
**Depends on:** LVM-2003 (PDF export — skill should include PDF output capability)

---

## What

Package TradingAgents as an OpenClaw skill and publish to ClawHub.ai, so any LLM with OpenClaw can run stock analysis by natural language (e.g., "分析微软").

### Current State

| Item | Status |
|------|--------|
| SKILL.md | Not exists |
| ClawHub listing | None |
| CLI script for LLM use | None |

### Target State

A published skill on ClawHub that LLMs can discover and use to run TradingAgents analysis.

## Why

Making TradingAgents available as an OpenClaw skill allows any LLM on the ClawHub ecosystem to run stock analysis without manual setup. Users just say "分析微软" and the LLM handles installation, configuration, and execution.

## Impact Analysis

- **Systems affected:** New files only (`SKILL.md`, `scripts/analyze.py`, `references/`)
- **Rollback plan:** Remove skill from ClawHub via `clawhub skill unpublish`
- **Risk:** Low — additive, no production code changes

## Implementation Plan

### Phase 1: Create skill structure

**Files to create:**

```
skill/
├── SKILL.md                    # Skill definition (YAML frontmatter + instructions)
├── scripts/
│   └── analyze.py              # Standalone CLI: analyze.py --ticker MSFT --date 2026-04-04
└── references/
    └── architecture.md         # Architecture reference (from README)
```

**SKILL.md frontmatter:**

```yaml
---
name: tradingagents
description: "Multi-agent LLM stock analysis. Analyze any stock and get a trading decision (BUY/SELL/HOLD). Supports US, Japan, HK, UK, Canada markets."
version: 1.0.0
metadata:
  openclaw:
    requires:
      env: [ZAI_API_KEY]
      bins: [python3, pip]
    primaryEnv: ZAI_API_KEY
    emoji: "📈"
    homepage: https://github.com/frankyxhl/TradingAgents
---
```

**scripts/analyze.py** interface:

```bash
# Basic usage
python analyze.py --ticker MSFT

# With options
python analyze.py --ticker 6861.T --date 2026-04-04 --language Chinese --output pdf
```

### Phase 2: Test locally

1. Install OpenClaw locally
2. Load skill: `openclaw skill load ./skill`
3. Test with natural language: "分析微软"、"analyze AAPL"、"6861.T の分析"
4. Verify: installation prompt, API key check, analysis execution, result formatting

### Phase 3: Publish to ClawHub

```bash
clawhub login
clawhub skill publish ./skill \
  --slug tradingagents \
  --name "TradingAgents" \
  --version 1.0.0 \
  --tags latest
```

## Approval

- [ ] Approved by: —

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-05 | Initial version — skill packaging plan for ClawHub | Frank + Claude Code |
