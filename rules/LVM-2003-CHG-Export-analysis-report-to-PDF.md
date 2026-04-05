# CHG-2003: Export analysis report to PDF

**Applies to:** LVM project
**Last updated:** 2026-04-05
**Last reviewed:** 2026-04-05
**Status:** Proposed
**Date:** 2026-04-05
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal

---

## What

Add PDF export capability to TradingAgents. After running an analysis, the system can generate a formatted PDF report in addition to the existing HTML output.

### Current State

| Item | Status |
|------|--------|
| HTML report | `tradingagents/render_report.py` generates HTML |
| PDF export | Not exists |
| CLI `--output` flag | Not exists |

### Target State

```python
# Python API
ta = TradingAgentsGraph(debug=True, config=config)
state, decision = ta.propagate("MSFT", "2026-04-04")
# Export to PDF
from tradingagents.render_report import render_pdf
render_pdf(state, output_path="MSFT_2026-04-04.pdf")
```

```bash
# CLI
tradingagents --ticker MSFT --output pdf

# Script
python scripts/analyze.py --ticker MSFT --output pdf
```

## Why

PDF is the standard format for sharing financial reports. HTML requires a browser; PDF can be emailed, printed, archived, and attached to trading records. For the OpenClaw skill (LVM-2002), PDF output makes the analysis result portable and professional.

## Impact Analysis

- **Systems affected:** `tradingagents/render_report.py` (add `render_pdf`), `pyproject.toml` (new dependency)
- **Rollback plan:** Remove `render_pdf` function, remove dependency
- **Risk:** Low — additive feature, existing HTML path unchanged

## Implementation Plan

### Phase 1: Choose PDF library

| Library | Pros | Cons |
|---------|------|------|
| `weasyprint` | CSS support, HTML→PDF, high quality | Heavy dependency (cairo, pango) |
| `pdfkit` / `wkhtmltopdf` | Good HTML→PDF | Requires system binary |
| `fpdf2` | Pure Python, lightweight, no system deps | No HTML→CSS, manual layout |
| `playwright` | Headless browser, perfect rendering | Very heavy |

**Recommendation:** `weasyprint` — best balance of quality and HTML reuse. We already have `render_html()` that produces styled HTML; `weasyprint` converts it directly to PDF with CSS intact.

**Fallback:** If `weasyprint` system deps are too heavy for users, provide `fpdf2` as a lightweight alternative with simpler formatting.

### Phase 2: Implement `render_pdf`

Add to `tradingagents/render_report.py`:

```python
def render_pdf(data: dict, output_path: str = None) -> str:
    """Render analysis report to PDF.
    
    Args:
        data: Full state dict from TradingAgentsGraph.propagate()
        output_path: Output file path. If None, auto-generates from ticker+date.
    
    Returns:
        Path to generated PDF file.
    """
    html = render_html(data)
    if output_path is None:
        ticker = data["company_of_interest"]
        date = data["trade_date"]
        output_path = f"{ticker}_{date}_report.pdf"
    
    from weasyprint import HTML
    HTML(string=html).write_pdf(output_path)
    return output_path
```

### Phase 3: Add CLI flag

Update `scripts/analyze.py` (for OpenClaw skill) to support `--output pdf`:

```bash
python analyze.py --ticker MSFT --output pdf    # generates MSFT_2026-04-04_report.pdf
python analyze.py --ticker MSFT --output html   # generates HTML (default)
python analyze.py --ticker MSFT --output both   # generates both
```

### Phase 4: Add dependency

```toml
# pyproject.toml
[project.optional-dependencies]
pdf = ["weasyprint>=62.0"]
dev = [
    "pytest>=9.0",
    "pytest-cov>=7.0",
    "pytest-bdd>=8.0",
    "ruff>=0.11",
]
```

Install: `pip install tradingagents[pdf]`

### Phase 5: Tests

- Test `render_pdf` with mock data (verify PDF file is created, non-empty)
- Test without `weasyprint` installed (graceful error message)
- Test `--output` flag in analyze.py

## Execution Order

```
Phase 1: Choose library (decision → ADR if needed)
    ▼
Phase 2: Implement render_pdf
    ▼
Phase 3: CLI flag
    ▼
Phase 4: Add dependency
    ▼
Phase 5: Tests
    ▼
LVM-2002: Package skill with PDF support
```

## Approval

- [ ] Approved by: —

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-05 | Initial version — PDF export plan with weasyprint | Frank + Claude Code |
