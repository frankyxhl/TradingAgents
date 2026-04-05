# SOP-1000: Workflow Routing PRJ

**Applies to:** TradingAgents (Livermore fork)
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Active

---

## What Is It?

Project-level workflow routing for the Livermore fork of TradingAgents. Defines branch strategy, change classification, and testing requirements specific to this project.

---

## Why

This is a personal fork maintained in parallel with upstream. Customizations (Chinese localization, Z.AI provider, theme) must not conflict with upstream sync, and graph routing changes require special care due to LangGraph's node-name sensitivity.

---

## When to Use

- When `af guide` resolves workflow routing and the PRJ layer is consulted
- Before any code change on this project
- When syncing upstream updates

---

## When NOT to Use

- When working on upstream contributions (use main branch, follow upstream conventions)

---

## Project Context

```
Repository:  frankyxhl/TradingAgents (fork of TauricResearch/TradingAgents)
Remotes:     origin   = frankyxhl/TradingAgents
             upstream = TauricResearch/TradingAgents
LLM:         Z.AI GLM-5-Turbo (via Coding API)
API Key:     ZAI_API_KEY in .env
Language:    output_language = "Chinese"
```

---

## Branch Rules

| Branch | Purpose | Direct commit? |
|--------|---------|----------------|
| `main` | Track upstream, stay clean | NEVER |
| `livermore` | All custom development | YES |

```
Golden Rule: Always work on livermore. Never commit to main.
```

### Upstream Sync Procedure

```bash
git checkout main
git pull upstream main
git checkout livermore
git merge main
# Resolve conflicts if any, then test
python test_zai.py
```

---

## Change Classification

### Standard (no review needed)
- HTML report theme/style adjustments in `tradingagents/render_report.py`
- Adding new tickers to test scripts
- Documentation and comments

### Normal (test before commit)
- New LLM provider addition
- Agent prompt modifications (i18n, instructions)
- `tradingagents/render_report.py` logic changes
- CLI selection changes in `cli/utils.py`

### High Risk (test + careful review)
- Changes touching `conditional_logic.py` (graph routing)
- Changes to node names in `graph/setup.py`
- Changes to `latest_speaker` or `current_response` field formats
- Any change to hardcoded string labels used for LangGraph routing

```
WARNING: LangGraph routes by string matching on node names and
state fields (startswith, exact match). Changing label prefixes
(e.g. "Bull Analyst" → "看多分析师") MUST be paired with updates
to conditional_logic.py. This was learned on 2026-04-04.
```

---

## Testing Checklist

### Before every push → LVM-1001 (Pre-Push CI Gate)

All 4 automated checks (pytest, ruff check, ruff format, BDD) must pass locally before `git push`. See `af read LVM-1001` for details.

### Manual tests (when touching specific layers)

| Layer | Command | When to run |
|-------|---------|-------------|
| Data | `python test.py` | Changes to `dataflows/` |
| Full pipeline | `python test_zai.py` | End-to-end verification with Z.AI |
| Report render | `python -m tradingagents.render_report` | Changes to `tradingagents/render_report.py` |

Before committing Normal or High Risk changes, run at minimum the relevant layer test.

---

## Files NOT to Commit

| Path | Reason |
|------|--------|
| `.env` | Contains API keys |
| `eval_results/` | Generated analysis data |
| `.venv/` | Virtual environment |
| `results/` | Runtime output |

---

## Key Files

| File | Role |
|------|------|
| `tradingagents/llm_clients/openai_client.py` | Provider base URLs and API keys |
| `tradingagents/llm_clients/model_catalog.py` | Model options for CLI |
| `tradingagents/llm_clients/factory.py` | Provider → Client routing |
| `tradingagents/graph/conditional_logic.py` | LangGraph debate/risk routing |
| `tradingagents/agents/utils/agent_utils.py` | `get_language_instruction()` |
| `tradingagents/render_report.py` | JSON → HTML report renderer |
| `test_zai.py` | Quick test script |
| `cli/utils.py` | CLI provider/model selection |

---

## Steps

This is a routing SOP — no procedural steps. The Branch Rules, Change Classification, and Testing Checklist above define the routing rules.

### Ready to commit/push/PR?

→ Follow **LVM-1002** (Commit and Release Flow): `af read LVM-1002`

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version: branch strategy, change classification, testing checklist | Frank + Claude Code |
| 2026-04-04 | Update Testing Checklist to reference LVM-1001 (Pre-Push CI Gate), add automated test suite | Claude Code |
