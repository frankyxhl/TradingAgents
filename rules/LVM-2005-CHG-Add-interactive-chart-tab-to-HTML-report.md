# CHG-2005: Add interactive chart tab to HTML report

**Applies to:** TradingAgents (Livermore fork)
**Last updated:** 2026-04-06
**Last reviewed:** 2026-04-06
**Status:** Proposed
**Date:** 2026-04-06
**Requested by:** Frank
**Priority:** Medium
**Change Type:** Normal

---

## What

Add an interactive K-line chart tab to the HTML report using TradingView Lightweight Charts (v4.2.0, Apache 2.0). The chart tab sits alongside the existing analysis content, with daily/weekly toggle and light/dark theme switcher.

### Current State

HTML report is text-only: header → nav (anchor scroll links) → analysis sections → footer. No chart.

### Target State

```
Header + Badge
Nav: [行情图表] [分析报告]        ← two top-level tabs
─────────────────────────────────
Tab "行情图表" (hidden by default, shown on click):
  [日线] [周线]        [浅色] [深色]
  ┌─────────────────────────────┐
  │  Lightweight Charts K-line  │
  │  + Volume histogram         │
  └─────────────────────────────┘

Tab "分析报告" (visible by default):
  技术分析 | 情绪分析 | 新闻分析 | ...  ← existing anchor nav
  [existing analysis sections]
─────────────────────────────────
Footer
```

**Key design decision: progressive enhancement.** Without JavaScript (e.g., PDF/weasyprint), the analysis tab is visible and chart tab is hidden. JS adds tab switching. This means:
- PDF: shows analysis only (chart hidden via CSS), no behavior change
- Browser: interactive tabs + chart

## Why

Technical analysis text describes indicators and support/resistance levels, but a visual chart makes patterns immediately obvious. Demo (`keyence_chart_demo.html`, ~1MB) proved the approach works.

## Impact Analysis

- **Systems affected:** 5 source files + 1 new vendored JS + 1 new test file (see file summary)
- **Rollback plan:** Revert `trading_graph.py`, `render_report.py`, `pyproject.toml`; delete `tradingagents/static/` directory and `tests/test_chart_integration.py`
- **Risk:** Low — additive tab with progressive enhancement; existing analysis sections unchanged; chart hidden in PDF via CSS

### File size budget

| Component | Size |
|-----------|------|
| Lightweight Charts JS (vendored, minified) | ~160 KB |
| OHLCV daily data (5 years, ~1,250 bars) | ~140 KB |
| OHLCV weekly data (5 years, ~260 bars) | ~30 KB |
| **Chart overhead per report** | **~330 KB** |
| Current report HTML (no chart) | ~90 KB |
| **Total with chart** | **~420 KB** |

Using `period="5y"` (not `"max"`) bounds the data to ~1,250 daily bars regardless of listing history.

## Implementation Plan

### Step 1: Fetch OHLCV data in `propagate()` AFTER graph execution

**File: `tradingagents/graph/trading_graph.py`**

Add `_fetch_ohlcv()` method and call it between graph completion and `_log_state()`. This avoids carrying large read-only data through every LangGraph node. Pass `trade_date` to avoid future data leakage in backtests.

```python
def propagate(self, company_name, trade_date):
    self.ticker = company_name
    init_agent_state = self.propagator.create_initial_state(company_name, trade_date)
    args = self.propagator.get_graph_args()

    if self.debug:
        trace = []
        for chunk in self.graph.stream(init_agent_state, **args):
            if len(chunk["messages"]) == 0:
                pass
            else:
                chunk["messages"][-1].pretty_print()
                trace.append(chunk)
        final_state = trace[-1]
    else:
        final_state = self.graph.invoke(init_agent_state, **args)

    self.curr_state = final_state

    # ── NEW: Attach OHLCV data for chart (after graph, not during) ──
    final_state["ohlcv_daily"], final_state["ohlcv_weekly"] = (
        self._fetch_ohlcv(company_name, trade_date)
    )

    self._log_state(trade_date, final_state)
    return final_state, self.process_signal(final_state["final_trade_decision"])

def _fetch_ohlcv(self, ticker, trade_date):
    """Fetch OHLCV price data for chart rendering.

    Args:
        ticker: Stock ticker symbol (e.g., "6861.T")
        trade_date: Analysis date string (YYYY-MM-DD). Used as end date
                    to prevent future data leakage in backtests.

    Returns:
        Tuple of (daily_list, weekly_list). Each item is a dict with
        keys: time, open, high, low, close, volume.
        Returns ([], []) on failure.
    """
    daily, weekly = [], []
    try:
        import yfinance as yf
        from tradingagents.dataflows.stockstats_utils import yf_retry

        from datetime import datetime, timedelta
        end_dt = datetime.strptime(trade_date, "%Y-%m-%d")
        start_dt = (end_dt - timedelta(days=5 * 365)).strftime("%Y-%m-%d")
        hist = yf_retry(lambda: yf.Ticker(ticker).history(start=start_dt, end=trade_date))
        if hist.empty:
            return daily, weekly
        for date, row in hist.iterrows():
            daily.append({
                "time": date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })
        weekly_df = hist.resample("W-FRI").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum"
        }).dropna()
        for date, row in weekly_df.iterrows():
            weekly.append({
                "time": date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            f"Failed to fetch OHLCV for {ticker}: {exc}"
        )
    return daily, weekly
```

### Step 2: Persist OHLCV in `_log_state()`

**File: `tradingagents/graph/trading_graph.py`**

Add to the log dict inside `_log_state()`:

```python
"ohlcv_daily": final_state.get("ohlcv_daily", []),
"ohlcv_weekly": final_state.get("ohlcv_weekly", []),
```

### Step 3: Vendor Lightweight Charts JS

**New file: `tradingagents/static/lightweight-charts.min.js`**

```bash
mkdir -p tradingagents/static
curl -sL "https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js" \
  -o tradingagents/static/lightweight-charts.min.js
```

**Update `pyproject.toml`** — add `tradingagents` to package-data:

Before:
```toml
[tool.setuptools.package-data]
cli = ["static/*"]
```

After:
```toml
[tool.setuptools.package-data]
cli = ["static/*"]
tradingagents = ["static/*"]
```

### Step 4: Add chart tab to `render_html()`

**File: `tradingagents/render_report.py`**

**4a. Read OHLCV data and vendored JS:**

```python
ohlcv_daily = data.get("ohlcv_daily", [])
ohlcv_weekly = data.get("ohlcv_weekly", [])
has_chart = bool(ohlcv_daily)

lw_js = ""
if has_chart:
    lw_js_path = Path(__file__).parent / "static" / "lightweight-charts.min.js"
    if lw_js_path.exists():
        lw_js = lw_js_path.read_text()
    else:
        has_chart = False
```

**4b. Build top tab bar (only if chart exists):**

```python
if has_chart:
    top_nav = (
        '<div class="tab-bar">'
        '<button class="tab-btn" onclick="switchTab(\'chart\')">行情图表</button>'
        '<button class="tab-btn active" onclick="switchTab(\'analysis\')">分析报告</button>'
        '</div>'
    )
else:
    top_nav = ""
```

**4c. Chart section HTML (hidden by default):**

```python
if has_chart:
    chart_section = '''
    <div id="tab-chart" style="display:none">
      <div class="chart-controls">
        <button id="btn-daily" class="active" onclick="switchTF(\'daily\')">日线</button>
        <button id="btn-weekly" onclick="switchTF(\'weekly\')">周线</button>
        <span class="chart-sep"></span>
        <button id="btn-light" class="active" onclick="switchTheme(\'light\')">浅色</button>
        <button id="btn-dark" onclick="switchTheme(\'dark\')">深色</button>
      </div>
      <div id="chart-container" style="width:100%;height:calc(100vh - 160px)"></div>
    </div>'''
else:
    chart_section = ""
```

**4d. Wrap analysis in a div:**

```python
analysis_section = f'''
<div id="tab-analysis">
  <nav>{nav_items}</nav>
  <div class="container">{body_sections}</div>
</div>'''
```

**4e. Modify the final HTML template return.**

Current template (lines 277-358) returns:
```
<body>
  <div class="header">...</div>
  <nav>{nav_items}</nav>
  <div class="container">{body_sections}</div>
  <footer>...</footer>
</body>
```

Replace with:
```
<body>
  <div class="header">...</div>
  {top_nav}
  {chart_section}
  {analysis_section}
  <footer>...</footer>
  {chart_init_js}
</body>
```

The original `<nav>{nav_items}</nav>` and `<div class="container">{body_sections}</div>` are now inside `{analysis_section}` (from Step 4d).

**4f. Chart initialization JS (complete code from working demo):**

```python
if has_chart:
    # Build JS without f-strings to avoid brace escaping issues
    chart_js = """
var dailyData=DAILY_PLACEHOLDER;
var weeklyData=WEEKLY_PLACEHOLDER;
var container=document.getElementById('chart-container');
var currentTF='daily';
var currentTheme='light';

var themes={
    dark:{
        bg:'#131722',text:'#d1d4dc',grid:'#1e222d',border:'#363a45',
        volUp:'rgba(38,166,154,0.3)',volDown:'rgba(239,83,80,0.3)',
        bodyBg:'#131722',headerBg:'#131722',btnBorder:'#363a45',
        btnActive:'#2962ff',btnActiveColor:'#fff',btnColor:'#d1d4dc'
    },
    light:{
        bg:'#ffffff',text:'#333333',grid:'#f0f0f0',border:'#e0e0e0',
        volUp:'rgba(38,166,154,0.25)',volDown:'rgba(239,83,80,0.25)',
        bodyBg:'#f5f5f5',headerBg:'#ffffff',btnBorder:'#d0d0d0',
        btnActive:'#2962ff',btnActiveColor:'#fff',btnColor:'#333333'
    }
};

var chart=LightweightCharts.createChart(container,{
    layout:{background:{type:'solid',color:themes.light.bg},textColor:themes.light.text},
    grid:{vertLines:{color:themes.light.grid},horzLines:{color:themes.light.grid}},
    crosshair:{mode:LightweightCharts.CrosshairMode.Normal},
    rightPriceScale:{borderColor:themes.light.border},
    timeScale:{borderColor:themes.light.border,timeVisible:false}
});
var candleSeries=chart.addCandlestickSeries({
    upColor:'#26a69a',downColor:'#ef5350',
    borderDownColor:'#ef5350',borderUpColor:'#26a69a',
    wickDownColor:'#ef5350',wickUpColor:'#26a69a'
});
var volumeSeries=chart.addHistogramSeries({
    priceFormat:{type:'volume'},priceScaleId:'volume'
});
chart.priceScale('volume').applyOptions({scaleMargins:{top:0.8,bottom:0}});

function switchTF(tf){
    currentTF=tf;
    var data=tf==='daily'?dailyData:weeklyData;
    candleSeries.setData(data.map(function(d){
        return{time:d.time,open:d.open,high:d.high,low:d.low,close:d.close};
    }));
    var t=themes[currentTheme];
    volumeSeries.setData(data.map(function(d){
        return{time:d.time,value:d.volume,color:d.close>=d.open?t.volUp:t.volDown};
    }));
    chart.timeScale().fitContent();
    document.getElementById('btn-daily').className=tf==='daily'?'active':'';
    document.getElementById('btn-weekly').className=tf==='weekly'?'active':'';
}

function switchTheme(theme){
    currentTheme=theme;
    var t=themes[theme];
    chart.applyOptions({
        layout:{background:{type:'solid',color:t.bg},textColor:t.text},
        grid:{vertLines:{color:t.grid},horzLines:{color:t.grid}},
        rightPriceScale:{borderColor:t.border},
        timeScale:{borderColor:t.border}
    });
    document.getElementById('btn-light').className=theme==='light'?'active':'';
    document.getElementById('btn-dark').className=theme==='dark'?'active':'';
    switchTF(currentTF);
}

function switchTab(tab){
    document.getElementById('tab-chart').style.display=tab==='chart'?'block':'none';
    document.getElementById('tab-analysis').style.display=tab==='analysis'?'block':'none';
    var btns=document.querySelectorAll('.tab-btn');
    for(var i=0;i<btns.length;i++){
        btns[i].className=btns[i].textContent.indexOf(tab==='chart'?'图表':'报告')>=0?'tab-btn active':'tab-btn';
    }
    if(tab==='chart'){chart.resize(container.clientWidth,container.clientHeight);chart.timeScale().fitContent();}
}

switchTF('daily');
switchTheme('light');
window.addEventListener('resize',function(){
    if(document.getElementById('tab-chart').style.display!=='none'){
        chart.resize(container.clientWidth,container.clientHeight);
    }
});
""".replace("DAILY_PLACEHOLDER", json.dumps(ohlcv_daily)).replace("WEEKLY_PLACEHOLDER", json.dumps(ohlcv_weekly))

    chart_init_js = f"<script>{lw_js}</script>\n<script>{chart_js}</script>"
else:
    chart_init_js = ""
```

**4g. CSS for tab bar and chart controls (complete):**

**Important:** Since the existing `render_html()` return value is a Python f-string, all CSS braces must be doubled (`{{` / `}}`). The CSS below is shown in normal form for readability. When inserting into the f-string template, replace every `{` with `{{` and every `}` with `}}`.

```css
/* Normal CSS form (double all braces when inserting into the f-string) */
.tab-bar { display: flex; gap: 0; border-bottom: 2px solid var(--border);
           background: var(--surface); position: sticky; top: 0; z-index: 10; }
.tab-btn { padding: 0.8rem 1.5rem; border: none; background: transparent;
           color: var(--text-muted); font-size: 0.95rem; cursor: pointer;
           transition: color 0.15s; }
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom: 2px solid var(--accent);
                   margin-bottom: -2px; }
.chart-controls { padding: 12px 24px; display: flex; gap: 8px; align-items: center;
                  background: var(--surface); border-bottom: 1px solid var(--border); }
.chart-controls button { padding: 6px 16px; border: 1px solid var(--border);
                         border-radius: 4px; background: transparent; color: var(--text);
                         font-size: 13px; cursor: pointer; transition: all 0.15s; }
.chart-controls button:hover { background: #eef1f4; }
.chart-controls button.active { background: #2962ff; border-color: #2962ff; color: #fff; }
.chart-sep { width: 1px; height: 20px; background: var(--border); margin: 0 8px; }
```

### Step 5: Hide chart in PDF CSS

**File: `tradingagents/render_report.py`** (in `_PDF_CSS` constant)

Add:

```css
#tab-chart { display: none !important; }
.tab-bar { display: none !important; }
#tab-analysis { display: block !important; }
```

### Step 6: Tests

**File: `tests/test_chart_integration.py`** (new)

| Test | What it verifies |
|------|-----------------|
| `test_fetch_ohlcv_returns_daily_and_weekly` | Mock yfinance history → daily list has dicts with time/open/high/low/close/volume; weekly list is shorter |
| `test_fetch_ohlcv_failure_returns_empty` | Mock yfinance raises → returns `([], [])` |
| `test_fetch_ohlcv_empty_dataframe_returns_empty` | Mock yfinance returns empty DataFrame → returns `([], [])` |
| `test_fetch_ohlcv_passes_end_date` | Mock yfinance → verify `.history()` called with `end=trade_date` |
| `test_fetch_ohlcv_weekly_fewer_bars_than_daily` | len(weekly) < len(daily) |
| `test_render_html_with_ohlcv_includes_chart` | Pass OHLCV in data → `id="tab-chart"` in HTML, `LightweightCharts` in HTML |
| `test_render_html_without_ohlcv_no_chart` | Empty OHLCV → `id="tab-chart"` NOT in HTML |
| `test_render_html_backward_compatible_no_ohlcv_key` | Omit OHLCV keys entirely → no error, analysis renders normally |
| `test_pdf_css_hides_chart` | Verify `_PDF_CSS` contains `#tab-chart { display: none` |

### File summary (7 files)

| File | Change |
|------|--------|
| `tradingagents/graph/trading_graph.py` | Add `_fetch_ohlcv(ticker, trade_date)`, call in `propagate()` after graph, persist in `_log_state()` |
| `tradingagents/render_report.py` | Add chart tab to `render_html()`, tab/chart CSS, hide chart in `_PDF_CSS` |
| `tradingagents/static/lightweight-charts.min.js` | Vendored JS library (new file, ~160KB) |
| `tests/test_chart_integration.py` | 9 new tests |
| `pyproject.toml` | Add `tradingagents = ["static/*"]` to `[tool.setuptools.package-data]` |
| `rules/LVM-2005-CHG-*.md` | This document |
| `rules/LVM-0000-REF-Document-Index.md` | Auto-updated by af |

**Files NOT changed (confirmed no impact):**
- `tradingagents/graph/propagation.py` — OHLCV not in initial state
- `tradingagents/agents/utils/agent_states.py` — OHLCV not in AgentState TypedDict
- `scripts/analyze.py` — passes full state dict, OHLCV flows through automatically

## Approval

- [ ] Approved by: —

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-06 | Initial version | Frank + Claude Code |
| 2026-04-06 | R1 fix: move OHLCV to post-graph; bound to 5y; progressive enhancement; code snippets; rollback plan; file size budget | Claude Code |
| 2026-04-06 | R2 fix: add trade_date to _fetch_ohlcv (prevent future data leak); empty DataFrame guard; complete chart JS from demo; complete CSS; explicit pyproject.toml change; canonical yf_retry import; final HTML template assembly | Claude Code |
| 2026-04-06 | R3 fix: use explicit start/end dates instead of period+end; add CSS f-string brace escaping note | Claude Code |
