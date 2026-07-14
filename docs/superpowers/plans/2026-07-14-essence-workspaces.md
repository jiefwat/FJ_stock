# StockTS Essence Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove narration and repeated explanatory surfaces from the five core workspaces while preserving decisions, safety gates, and auditable evidence.

**Architecture:** Keep domain models and analysis orchestration unchanged. Simplify the five dedicated HTML renderers, pass legacy supporting panels into one default-closed evidence drawer per workspace, remove wrapper descriptions in `web.py`, and add a small shared CSS layer for the compact verdict-first hierarchy.

**Tech Stack:** Python 3.11, stdlib HTML rendering, pytest, BeautifulSoup test inspection, in-app browser responsive verification.

---

### Task 1: Lock The Essence Contract With Failing Tests

**Files:**
- Create: `tests/test_web_essence_mode.py`
- Modify: `tests/test_web_market_research_workspace.py`
- Modify: `tests/test_web_portfolio_dossier.py`
- Modify: `tests/test_web_stock_dossier.py`
- Modify: `tests/test_web_opportunity_dossier.py`
- Modify: `tests/test_web_data_center_workspace.py`

- [ ] **Step 1: Write the failing full-page narration test**

```python
def test_core_workspaces_remove_narration_and_decorative_labels() -> None:
    html = _sample_html()
    for phrase in (
        "当前时刻股票涨跌统计、强弱板块与分析。",
        "只维护和分析真实持仓",
        "用一份投委会档案",
        "先过市场与数据闸门",
        "先恢复可信数据，再恢复研究结论。",
        "RISK GOVERNANCE",
        "ACTION QUEUE",
        "RESEARCH FUNNEL",
        "RESTORE ORDER",
    ):
        assert phrase not in html
```

- [ ] **Step 2: Write failing renderer structure tests**

```python
def test_opportunity_front_row_is_three_and_evidence_is_closed() -> None:
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
    front = html.split('class="opportunity-evidence', 1)[0]
    assert front.count("data-opportunity-stock-row") == 3
    assert '<details class="opportunity-evidence' in html

def test_portfolio_front_row_is_three_and_has_one_evidence_drawer() -> None:
    dossier = _dossier()
    seed = dossier.queue[0]
    queue = tuple(
        replace(seed, code=f"6000{index:02d}", name=f"持仓{index:02d}", priority=index)
        for index in range(1, 8)
    )
    html = render_portfolio_workspace(replace(dossier, queue=queue))
    front = html.split('class="portfolio-evidence', 1)[0]
    assert front.count('class="portfolio-queue-item') == 3
    assert html.count('class="portfolio-evidence') == 1
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest \
  tests/test_web_essence_mode.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_stock_dossier.py \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_data_center_workspace.py -q
```

Expected: failures for current narration, five-item front rows, and missing unified evidence drawers.

- [ ] **Step 4: Commit the RED contract**

```bash
git add tests/test_web_essence_mode.py tests/test_web_*workspace.py tests/test_web_*dossier.py
git commit -m "[界面测试] 锁定全站精华模式契约"
```

### Task 2: Simplify Market And Shell

**Files:**
- Modify: `src/stock_ts/webapp/market_workspace.py`
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_essence_mode.py`
- Test: `tests/test_web_market_research_workspace.py`

- [ ] **Step 1: Remove shell and market wrapper narration**

Delete the sidebar note and all five core `.module-desc` paragraphs. Retain page titles, status pills, refresh controls, and account transaction labels.

- [ ] **Step 2: Replace duplicate market headings with compact phase labels**

Render one compact phase strip and remove `_session_heading`. Keep `data-primary-market-verdict`, market state, risk budget, confidence, trade date, thesis, primary risk, and invalidation.

- [ ] **Step 3: Consolidate market evidence**

```python
market_evidence = (
    '<details class="market-evidence essence-evidence">'
    '<summary>大盘证据</summary>'
    f'<div class="essence-evidence-body">{distribution_html}{intraday_detail_html}'
    f'{events_html}{close_html}{supporting_html}{audit_table}</div></details>'
)
```

Keep the risk decision rail, scenarios, and compact dimension conclusions visible. Move verbose panels into the drawer.

- [ ] **Step 4: Run market and essence tests**

Run:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest \
  tests/test_web_essence_mode.py tests/test_web_market_research_workspace.py \
  tests/test_web_app_shell.py tests/test_web_tdx_only_ui.py -q
```

Expected: market tests pass; unrelated renderer failures remain RED.

### Task 3: Simplify Portfolio And Stock

**Files:**
- Modify: `src/stock_ts/webapp/portfolio_workspace.py`
- Modify: `src/stock_ts/webapp/stock_workspace.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_portfolio_dossier.py`
- Test: `tests/test_web_stock_dossier.py`
- Test: `tests/test_web_stock_research_workspace.py`

- [ ] **Step 1: Reduce the portfolio front row**

Render only `dossier.queue[:3]` and the highest-severity exposure before the evidence drawer. Put the remaining queue, full exposure register, all position boundaries, and `supporting_evidence_html` inside one `portfolio-evidence essence-evidence` details block.

- [ ] **Step 2: Reduce repeated portfolio copy**

Remove metric notes, English eyebrows, cost-context narration when it repeats the reason, and the position-boundary explanatory paragraph. Preserve current weights, treatment reason, trigger, invalidation, and prohibited action.

- [ ] **Step 3: Reduce the stock decision surface**

Keep one verdict band, one compact trigger strip, up to three risk rows, and six execution boundary values. Remove English eyebrows and explanatory section paragraphs.

- [ ] **Step 4: Consolidate stock evidence**

Render diagnostic conclusions as compact visible rows. Put full diagnostic facts and risks, scenario source text, evidence ledger rows, `supporting_evidence_html`, technical panels, and role debate in one default-closed `stock-evidence essence-evidence` drawer.

- [ ] **Step 5: Run portfolio and stock tests**

Run:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest \
  tests/test_web_essence_mode.py tests/test_web_portfolio_dossier.py \
  tests/test_web_stock_dossier.py tests/test_web_stock_research_workspace.py \
  tests/test_web_professional.py tests/test_web_professional_copy.py -q
```

Expected: portfolio and stock structure, stale gate, evidence, and professional-copy tests pass.

### Task 4: Simplify Opportunities And Data Center

**Files:**
- Modify: `src/stock_ts/webapp/opportunity_workspace.py`
- Modify: `src/stock_ts/webapp/data_center_workspace.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_opportunity_dossier.py`
- Test: `tests/test_web_data_center_workspace.py`

- [ ] **Step 1: Compress the opportunity funnel**

Replace narrated funnel articles with compact name/count/status items. Keep the gate and four key metrics visible.

- [ ] **Step 2: Limit candidates and consolidate evidence**

Render three front candidates. Each front card keeps one support item, one counter item, state, strategy, date, next verification, and the stock link. Move remaining candidates, full risks beyond the first three, source notes, and `supporting_html` into one `opportunity-evidence essence-evidence` drawer.

- [ ] **Step 3: Compress data recovery**

Render at most three recovery items with category, status, issue, and verification. Render downstream module impact as compact rows. Keep the source ledger default closed.

- [ ] **Step 4: Run opportunity and data-center tests**

Run:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest \
  tests/test_web_essence_mode.py tests/test_web_opportunity_dossier.py \
  tests/test_web_data_center_workspace.py tests/test_web_data_accuracy.py -q
```

Expected: all new essence-mode tests pass.

### Task 5: Tighten Visual Rhythm And Verify Responsive Layout

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_essence_mode.py`
- Modify: `docs/superpowers/essence-workspaces/TODO.md`
- Create: `docs/superpowers/essence-workspaces/test.md`

- [ ] **Step 1: Add focused compact CSS**

Add `.essence-*` rules for the primary verdict band, compact phase/count strips, thin secondary dividers, one evidence drawer treatment, and mobile stacking. Preserve the existing palette and navigation.

- [ ] **Step 2: Add CSS contract assertions**

```python
def test_essence_css_has_mobile_focus_and_reduced_motion_contracts() -> None:
    assert ".essence-evidence" in CSS
    assert ".essence-strip" in CSS
    assert "@media (max-width: 760px)" in CSS
    assert ":focus-visible" in CSS
    assert "prefers-reduced-motion" in CSS
```

- [ ] **Step 3: Run focused and full regression tests**

Run:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest \
  tests/test_web_essence_mode.py tests/test_web_*.py -q
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q
make lint
```

Expected: no new failures. Document the known `tests/test_daily_pipeline.py` baseline separately if it remains reproducible.

- [ ] **Step 4: Verify real pages**

Start the local server on an unused port and inspect all five routes at `1440x1000` and `390x844`. Record visible height, text count, horizontal overflow, drawer state, and console errors. Reload after source changes.

- [ ] **Step 5: Review and update requirement evidence**

Write `docs/superpowers/essence-workspaces/test.md`, check completed TODO items, run `git diff --check`, and review the diff for deleted safety gates or inaccessible evidence.

### Task 6: Integrate And Deploy

**Files:**
- Create: `docs/superpowers/essence-workspaces/review.md`

- [ ] **Step 1: Commit verified implementation**

Use repository-style Chinese scoped commits after tests, lint, browser checks, and diff review have fresh evidence.

- [ ] **Step 2: Fast-forward `main` and push**

Verify the isolated worktree is clean, fast-forward the integration `main`, push `origin/main`, and confirm GitHub `main` matches local `main`.

- [ ] **Step 3: Deploy with Git bundle**

Transfer the verified commit without overwriting `.env`, `.secrets`, `data`, `reports`, Nginx, systemd timers, Signal Desk, or DSA. Restart only `stock-ts.service` unless another changed component requires it.

- [ ] **Step 4: Refresh production data and verify parity**

Run the established production refresh pipeline, then verify local HEAD, local `main`, `origin/main`, GitHub `main`, and server HEAD are identical. Confirm `stock-ts.service`, Signal Desk, both timers, Nginx, server `/healthz`, and public `/healthz` are healthy.
