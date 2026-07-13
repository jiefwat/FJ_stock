# Research Terminal Density V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the StockTs research terminal faster to scan on desktop and mobile by introducing a dominant global action tape and progressive disclosure for dense portfolio and opportunity records.

**Architecture:** Keep the existing server-rendered dossier models and route shell. Change only presentation orchestration: `web.py` emits semantic freshness roles, focused `webapp` renderers split front-row and overflow records, and `styles.py` owns the responsive visual hierarchy. Native `details/summary` preserves all records without adding client-side state.

**Tech Stack:** Python 3.9+, stdlib HTML rendering, CSS grid, native HTML disclosure, pytest, ruff, in-app browser responsive smoke.

---

### Task 1: Build The Global Research Tape Contract

**Files:**
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_layout.py`
- Modify: `tests/test_web_data_accuracy.py`

- [ ] **Step 1: Write failing structure tests**

Add these assertions to a new test in `tests/test_web_layout.py`:

```python
def test_global_freshness_surface_is_action_first_research_tape() -> None:
    html = render_page(stock_code="600519", holdings_path="data/portfolio/holdings.csv")
    start = html.index('class="freshness-bar research-tape"')
    end = html.index('</section>', start)
    tape = html[start:end]

    assert 'data-gate-level=' in tape
    assert tape.index("动作闸门") < tape.index("数据状态")
    assert tape.index("数据状态") < tape.index("交易日")
    assert 'class="research-tape-primary"' in tape
    assert tape.count('class="research-tape-item core"') == 2
    assert tape.count('class="research-tape-item secondary"') == 3
    assert 'class="research-tape-data-link" href="#data-center"' in tape
```

Extend the stale-data test in `tests/test_web_data_accuracy.py`:

```python
assert 'data-gate-level="high"' in html
assert "暂停行动" in html
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_layout.py::test_global_freshness_surface_is_action_first_research_tape \
  tests/test_web_data_accuracy.py
```

Expected: the new layout test fails because the current freshness surface has six equal anonymous `div` items and no data-center route.

- [ ] **Step 3: Implement semantic action-first markup**

Replace `_render_global_freshness_bar` in `src/stock_ts/web.py` with markup equivalent to:

```python
return f"""
  <section class="freshness-bar research-tape" data-gate-level="{escape(risk_gate.level)}"
    aria-label="全局研究状态">
    <div class="research-tape-primary">
      <span>动作闸门</span><strong>{escape(risk_gate.gate)}</strong>
      <small>{escape(risk_gate.reason)}</small>
    </div>
    <div class="research-tape-item core"><span>数据状态</span>
      <strong>{escape(quality.signal)}</strong></div>
    <div class="research-tape-item core"><span>交易日</span>
      <strong>{escape(market.trade_date or quality.market_date or '待确认')}</strong></div>
    <div class="research-tape-item secondary"><span>行情日期</span>
      <strong>{escape(quality.latest_date or '待确认')}</strong></div>
    <div class="research-tape-item secondary"><span>证据覆盖</span>
      <strong>{escape(data_detail)}</strong></div>
    <div class="research-tape-item secondary"><span>来源</span>
      <strong>{escape(provider_label)}</strong></div>
    <a class="research-tape-data-link" href="#data-center">数据详情 <span>→</span></a>
  </section>"""
```

Keep `risk_gate.level`, `risk_gate.reason`, all escaped provider/data strings, and the existing data-center summary unchanged.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q tests/test_web_layout.py tests/test_web_data_accuracy.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit the research-tape contract**

```bash
git add src/stock_ts/web.py tests/test_web_layout.py tests/test_web_data_accuracy.py
git commit -m '[界面层级] 建立行动优先研究状态带'
```

### Task 2: Compact The Mobile Shell And Style The Research Tape

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_design_guide_shell.py`
- Modify: `tests/test_web_layout.py`

- [ ] **Step 1: Write failing CSS-contract tests**

Add to `tests/test_web_design_guide_shell.py`:

```python
def test_research_tape_and_mobile_shell_have_explicit_density_rules() -> None:
    for selector in [
        ".research-tape-primary",
        ".research-tape-item.secondary",
        ".research-tape-data-link",
        '.research-tape[data-gate-level="high"]',
    ]:
        assert selector in CSS
    mobile = CSS.split("@media (max-width: 680px)")[-1]
    assert ".quick-stock-search" in mobile
    assert "grid-template-columns:minmax(0,1fr)auto" in mobile.replace(" ", "")
    assert ".research-tape-item.secondary" in mobile
    assert "display:none" in mobile.replace(" ", "")
```

Add a focus assertion:

```python
assert ".research-tape-data-link:focus-visible" in CSS
```

- [ ] **Step 2: Run the CSS tests and confirm RED**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_design_guide_shell.py::test_research_tape_and_mobile_shell_have_explicit_density_rules
```

Expected: failure because the new selectors do not exist.

- [ ] **Step 3: Add desktop Research Tape styling**

Replace the old generic freshness rules with a seven-part tape:

```css
.research-tape {
  grid-template-columns:minmax(190px,1.35fr) repeat(5,minmax(110px,1fr)) auto;
  gap:0;
  padding:0;
  overflow:hidden;
  border-radius:18px;
  background:#fffdf8;
}
.research-tape-primary {
  display:grid;
  align-content:center;
  gap:4px;
  padding:13px 16px;
  color:#edf5fa;
  background:linear-gradient(135deg,#10283d,#173a55);
}
.research-tape-primary span,
.research-tape-item span { font-family:var(--mono); font-size:9px; letter-spacing:.07em; }
.research-tape-primary strong { font-size:18px; }
.research-tape-primary small { color:#b9cad6; line-height:1.35; }
.research-tape-item {
  display:grid;
  align-content:center;
  gap:5px;
  min-width:0;
  padding:12px;
  border-left:1px solid var(--line);
}
.research-tape-data-link {
  display:grid;
  place-items:center;
  padding:12px;
  color:var(--brand);
  font-size:11px;
  font-weight:900;
  background:var(--accent-soft);
}
.research-tape[data-gate-level="high"] .research-tape-primary {
  background:linear-gradient(135deg,#472527,#7d342f);
}
```

Add `.research-tape-data-link:focus-visible` to the existing focus selector group.

- [ ] **Step 4: Add mobile shell compression**

Inside the final `@media (max-width: 680px)` block add:

```css
.brand-subtitle { display:none; }
.quick-stock-search {
  grid-template-columns:minmax(0,1fr) auto;
  gap:7px;
  padding:8px;
}
.quick-stock-search button { white-space:nowrap; padding-inline:14px; }
.nav-item { flex-basis:112px; }
.research-tape {
  position:relative;
  top:auto;
  grid-template-columns:repeat(2,minmax(0,1fr));
  margin-bottom:9px;
}
.research-tape-primary,
.research-tape-data-link { grid-column:1 / -1; }
.research-tape-item.secondary { display:none; }
.research-tape-data-link { grid-template-columns:auto auto; justify-content:space-between; }
```

Do not hide the action gate, data state, trading date, or data-center route.

- [ ] **Step 5: Run shell and responsive regression tests**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_design_guide_shell.py \
  tests/test_web_layout.py \
  tests/test_web_app_shell.py \
  tests/test_web_compact_mode.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit the shell design**

```bash
git add src/stock_ts/webapp/styles.py tests/test_web_design_guide_shell.py tests/test_web_layout.py
git commit -m '[界面层级] 压缩移动端研究壳层'
```

### Task 3: Add Opportunity Front-Row Disclosure

**Files:**
- Modify: `src/stock_ts/webapp/opportunity_workspace.py`
- Modify: `tests/test_web_opportunity_dossier.py`

- [ ] **Step 1: Write a failing preservation-and-disclosure test**

Import `replace` from `dataclasses`, then add:

```python
def test_opportunity_workspace_keeps_six_front_candidates_and_all_records() -> None:
    dossier = _dossier()
    seed = dossier.candidates[0]
    candidates = tuple(
        replace(seed, code=f"6000{index:02d}", name=f"候选{index:02d}")
        for index in range(1, 9)
    )
    html = render_opportunity_workspace(
        replace(dossier, candidates=candidates),
        provider_name="sample",
        holdings_path="data/portfolio/holdings.csv",
    )

    assert html.count("data-opportunity-stock-row") == 8
    front = html.split('class="candidate-overflow"', 1)[0]
    assert front.count("data-opportunity-stock-row") == 6
    assert "查看其余 2 只候选" in html
    assert html.count("进入个股分析") == 8
```

- [ ] **Step 2: Run the test and confirm RED**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_opportunity_dossier.py::test_opportunity_workspace_keeps_six_front_candidates_and_all_records
```

Expected: failure because all eight candidates are rendered into one grid and no overflow disclosure exists.

- [ ] **Step 3: Split candidate rendering without dropping records**

In `render_opportunity_workspace` use:

```python
front_candidates = dossier.candidates[:6]
overflow_candidates = dossier.candidates[6:]
candidates = "".join(
    _render_candidate(item, provider_name=provider_name, holdings_path=holdings_path)
    for item in front_candidates
)
overflow = ""
if overflow_candidates:
    overflow_cards = "".join(
        _render_candidate(item, provider_name=provider_name, holdings_path=holdings_path)
        for item in overflow_candidates
    )
    overflow = (
        '<details class="candidate-overflow research-overflow">'
        f'<summary>查看其余 {len(overflow_candidates)} 只候选</summary>'
        f'<div class="candidate-decision-grid">{overflow_cards}</div></details>'
    )
```

Render `{overflow}` immediately after the always-visible candidate grid. Preserve the existing empty state when no candidates exist.

- [ ] **Step 4: Run opportunity tests and confirm GREEN**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_opportunity_dossier.py \
  tests/test_opportunity_dossier.py \
  tests/test_sector_candidates.py
```

Expected: all tests pass and every candidate link remains present.

- [ ] **Step 5: Commit opportunity disclosure**

```bash
git add src/stock_ts/webapp/opportunity_workspace.py tests/test_web_opportunity_dossier.py
git commit -m '[机会研究] 收敛候选前排展示密度'
```

### Task 4: Add Portfolio Queue And Boundary Disclosure

**Files:**
- Modify: `src/stock_ts/webapp/portfolio_workspace.py`
- Modify: `tests/test_web_portfolio_dossier.py`

- [ ] **Step 1: Write failing queue and boundary preservation tests**

Import `replace` from `dataclasses`, then add:

```python
def test_portfolio_workspace_limits_front_row_without_losing_audit_records() -> None:
    dossier = _dossier()
    queue_seed = dossier.queue[0]
    boundary_seed = dossier.boundaries[0]
    queue = tuple(
        replace(queue_seed, code=f"6000{index:02d}", name=f"持仓{index:02d}")
        for index in range(1, 8)
    )
    boundaries = tuple(
        replace(boundary_seed, code=f"6000{index:02d}", name=f"持仓{index:02d}")
        for index in range(1, 7)
    )
    html = render_portfolio_workspace(replace(dossier, queue=queue, boundaries=boundaries))

    assert html.count('class="portfolio-queue-item') == 7
    front_queue = html.split('class="portfolio-queue-overflow', 1)[0]
    assert front_queue.count('class="portfolio-queue-item') == 5
    assert "查看其余 2 项处置" in html
    assert html.count('class="portfolio-boundary-card') == 6
    assert "查看其余 2 项边界" in html
```

- [ ] **Step 2: Run the test and confirm RED**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_portfolio_dossier.py::test_portfolio_workspace_limits_front_row_without_losing_audit_records
```

Expected: failure because no overflow disclosures exist.

- [ ] **Step 3: Extract item render helpers**

Move the existing queue and boundary HTML into:

```python
def _render_queue_item(item: PortfolioQueueItem) -> str:
    return (
        f'<article class="portfolio-queue-item state-{_state_class(item.state)}">'
        f'<header><span>#{item.priority:02d}</span><div><strong>{escape(item.name)}</strong>'
        f'<small>{escape(item.code)} · 当前权重 {item.current_weight:.1%}</small></div>'
        f'<em>{escape(item.state)}</em></header>'
        f'<p class="portfolio-cost-context">{escape(item.cost_context)}</p>'
        '<div class="portfolio-queue-reason"><span>处置依据</span>'
        f'<p>{escape(item.reason)}</p></div>'
        '<div class="portfolio-trigger-pair"><div><span>复核触发</span>'
        f'<strong>{escape(item.trigger)}</strong></div><div><span>失效条件</span>'
        f'<strong>{escape(item.invalidation)}</strong></div></div></article>'
    )


def _render_boundary(item: PortfolioBoundary) -> str:
    return (
        '<article class="portfolio-boundary-card">'
        f'<header><div><strong>{escape(item.name)}</strong><small>{escape(item.code)}</small></div>'
        f'<em>{escape(item.current_action)}</em></header>'
        f'<dl><div><dt>持仓边界</dt><dd>{escape(item.target_range)}</dd></div>'
        f'<div><dt>降低风险触发</dt><dd>{escape(item.reduce_trigger)}</dd></div>'
        f'<div><dt>失效条件</dt><dd>{escape(item.invalidation)}</dd></div></dl>'
        '<p class="portfolio-prohibited"><span>禁止动作</span>'
        f'{escape(item.prohibited_action)}</p></article>'
    )
```

Import `PortfolioBoundary` and `PortfolioQueueItem` from the model module. The helper bodies must retain every existing `escape()` call and numeric formatting.

- [ ] **Step 4: Split front rows and overflow records**

Use five queue and four boundary records as the visible limits:

```python
queue_front = "".join(_render_queue_item(item) for item in dossier.queue[:5])
queue_rest = "".join(_render_queue_item(item) for item in dossier.queue[5:])
queue_overflow = _render_overflow(
    "portfolio-queue-overflow",
    f"查看其余 {max(0, len(dossier.queue) - 5)} 项处置",
    "portfolio-treatment-queue",
    queue_rest,
)

boundary_front = "".join(_render_boundary(item) for item in dossier.boundaries[:4])
boundary_rest = "".join(_render_boundary(item) for item in dossier.boundaries[4:])
boundary_overflow = _render_overflow(
    "portfolio-boundary-overflow",
    f"查看其余 {max(0, len(dossier.boundaries) - 4)} 项边界",
    "portfolio-boundary-grid",
    boundary_rest,
)
```

Define `_render_overflow(css_class, summary, grid_class, content)` to return an empty string when `content` is empty, otherwise a native details block with escaped summary text.

- [ ] **Step 5: Run portfolio and stale-safety tests**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_portfolio_dossier.py \
  tests/test_portfolio_dossier.py \
  tests/test_web_portfolio_interaction.py \
  tests/test_portfolio_advice.py
```

Expected: all tests pass; stale numeric actions remain absent.

- [ ] **Step 6: Commit portfolio disclosure**

```bash
git add src/stock_ts/webapp/portfolio_workspace.py tests/test_web_portfolio_dossier.py
git commit -m '[组合研究] 收敛处置与边界展示密度'
```

### Task 5: Style Progressive Disclosure And Wide-Screen Context

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_design_guide_shell.py`

- [ ] **Step 1: Write failing disclosure-style tests**

Add:

```python
def test_dense_research_records_use_shared_disclosure_visuals() -> None:
    for selector in [
        ".research-overflow",
        ".research-overflow summary",
        ".candidate-overflow",
        ".portfolio-queue-overflow",
        ".portfolio-boundary-overflow",
    ]:
        assert selector in CSS
    assert "position:sticky" in CSS.replace(" ", "")
    assert ".opportunity-risk-register" in CSS
```

- [ ] **Step 2: Run the test and confirm RED**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_design_guide_shell.py::test_dense_research_records_use_shared_disclosure_visuals
```

Expected: failure because shared disclosure selectors do not exist.

- [ ] **Step 3: Add disciplined disclosure visuals**

Add:

```css
.research-overflow {
  margin-top:12px;
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:14px;
  background:rgba(255,253,248,.72);
}
.research-overflow summary {
  cursor:pointer;
  list-style:none;
  padding:13px 15px;
  color:var(--brand);
  font-size:12px;
  font-weight:900;
}
.research-overflow summary::after { content:"＋"; float:right; color:var(--accent); }
.research-overflow[open] summary::after { content:"－"; }
.research-overflow > div { padding:0 12px 12px; }
.candidate-overflow,
.portfolio-queue-overflow,
.portfolio-boundary-overflow { width:100%; }
@media (min-width: 921px) {
  .opportunity-risk-register { position:sticky; top:92px; }
}
@media (max-width: 680px) {
  .research-overflow { border-radius:12px; }
  .research-overflow > div { padding:0 8px 8px; }
}
```

Add `.research-overflow summary:focus-visible` to the focus selector group.

- [ ] **Step 4: Run full Web layout suites**

Run:

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_design_guide_shell.py \
  tests/test_web_layout.py \
  tests/test_web_module_decisions.py \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_compact_mode.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit disclosure visuals**

```bash
git add src/stock_ts/webapp/styles.py tests/test_web_design_guide_shell.py
git commit -m '[界面设计] 统一研究记录渐进展开样式'
```

### Task 6: Verify, Review, Integrate, And Deploy

**Files:**
- Modify: `docs/product/stock-analysis-agent-design-guide.md`
- Modify: `docs/superpowers/research-terminal-density-v2/TODO.md`
- Modify: `docs/superpowers/research-terminal-density-v2/test.md`
- Modify: `docs/superpowers/research-terminal-density-v2/review.md`

- [ ] **Step 1: Run fresh static and focused verification**

```bash
make lint
git diff --check
python3 -m compileall -q src/stock_ts
PYTHONPATH=src <python> -m pytest -q \
  tests/test_web_design_guide_shell.py \
  tests/test_web_layout.py \
  tests/test_web_data_accuracy.py \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_module_decisions.py
```

Expected: ruff and compileall pass; focused tests have zero failures.

- [ ] **Step 2: Run Python 3.9 contracts**

```bash
PYTHONPATH=src python3.9 -m pytest -q \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_market_research_workspace.py
```

Expected: zero failures.

- [ ] **Step 3: Run full pytest and compare the known baseline**

```bash
PYTHONPATH=src <python> -m pytest -q
```

Expected: no failure beyond the five documented daily-pipeline baseline tests.

- [ ] **Step 4: Perform responsive browser smoke**

Start the current worktree on a temporary port. Verify at `1440x1000` and `390x844`:

- no horizontal overflow;
- one primary verdict per business workspace;
- mobile research tape shows the action gate, data state, trading date, and data-center route;
- mobile module title or primary verdict starts earlier than the deployed baseline;
- opportunity front row has six cards and its disclosure preserves all candidates;
- portfolio front row has five queue cards and four boundaries and its disclosures preserve all records.

- [ ] **Step 5: Update evidence and product documentation**

Record exact commands, counts, viewport measurements, review findings, commit hashes, and deployment boundaries in the requirement directory. Update the product design guide to state that global metadata must not consume the mobile first screen and dense records use front-row plus audit disclosure.

- [ ] **Step 6: Commit quality evidence**

```bash
git add docs/product/stock-analysis-agent-design-guide.md \
  docs/superpowers/research-terminal-density-v2
git commit -m '[研究终端] 完成密度升级验收记录'
```

- [ ] **Step 7: Fast-forward `main`, push, and deploy**

Fetch `origin/main`, require it to be an ancestor of the feature branch, fast-forward local `main`, push `origin/main`, create a server source backup, deploy by `ff-only`, restart `stock-ts.service`, and verify:

```text
local main == GitHub origin/main == server main
stock-ts.service == active
stock-ts-signal-desk.service == active
nginx == active
server /healthz == 200 ok
public /healthz == 200 ok
```

Preserve `.env`, `.secrets`, data, reports, Nginx, timers, and DSA.
