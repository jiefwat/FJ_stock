# Professional Workbench Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the StockTs web page more professional, effective, reliable, and easy for manual interaction while preserving the four-module product shape.

**Architecture:** Keep the existing stdlib web renderer and four workspaces. Add a global decision strip around the existing data center, then rename and reorder visible module sections so each workspace starts with conclusion, risk, and manual actions. Use existing view models and HTML helpers; do not introduce frontend dependencies.

**Tech Stack:** Python 3.11, stdlib HTML rendering in `src/stock_ts/web.py`, CSS in `src/stock_ts/webapp/styles.py`, pytest and ruff.

---

### Task 1: Global Data Center Interaction Layout

**Files:**
- Modify: `src/stock_ts/web.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_module_decisions.py`

- [ ] **Step 1: Write tests for a compact professional data center**

Add assertions that the rendered page contains `专业数据中台`, `人工复核入口`, `影响分析预警`, data domains, and module jump targets.

- [ ] **Step 2: Implement global data center cards and anchor links**

Render a compact status card row before the data table and add row ids for `data-domain-kline`, `data-domain-news`, `data-domain-announcement`, `data-domain-fundamental`, and `data-domain-fund`.

- [ ] **Step 3: Add CSS for sticky/compact professional layout**

Add `.data-center-kpi-grid`, `.data-center-row.blocked`, `.data-center-row.warn`, `.manual-action-grid`, and mobile fallbacks.

- [ ] **Step 4: Verify targeted tests**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_web_module_decisions.py -q`
Expected: all tests pass.

### Task 2: Four Module Section Alignment

**Files:**
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_module_decisions.py`

- [ ] **Step 1: Update tests for required business section labels**

Assert labels from the four MD specs: market summary/risk/index/breadth/sector/movers/data quality; portfolio summary/risk budget/queue/details/exposure/boundary/ledger/data quality; stock input/summary/conclusion/six evidence blocks/source/data quality; opportunity status/strategy/candidates/filter/risk/sector/sentiment/data quality.

- [ ] **Step 2: Rename visible headings without changing data contracts**

Replace metaphorical headings with business terms and keep old critical text only when current tests or navigation need it.

- [ ] **Step 3: Move risk and manual actions closer to first screen**

Use existing HTML order where possible; add lightweight action cards linking to existing modules or data center anchors.

- [ ] **Step 4: Verify targeted tests**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_web_module_decisions.py tests/test_web_layout.py tests/test_web_app_shell.py tests/test_web_compact_mode.py -q`
Expected: all tests pass.

### Task 3: Final Verification and Release

**Files:**
- Modify only code/tests/this plan; do not stage the user's four product MD edits.

- [ ] **Step 1: Run full tests**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q`
Expected: all tests pass with only known AKShare warnings.

- [ ] **Step 2: Run lint**

Run: `PYTHONPATH=src .venv/bin/python -m ruff check src tests scripts/eltdx_bridge.py`
Expected: `All checks passed!`

- [ ] **Step 3: Restart local web service and smoke check**

Run service on `127.0.0.1:8505`, then GET `/healthz` and page HTML. Confirm the new labels render.

- [ ] **Step 4: Commit and push**

Stage only implementation files and the plan. Commit message: `[页面布局] 优化专业工作台交互`. Push `main` to GitHub.
