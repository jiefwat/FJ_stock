# StockTS Simple Nine-Module Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the StockTS web workbench into a simple nine-module A-share product shell aligned with direct user tasks.

**Architecture:** Keep the current Python HTTP server and module render functions, but replace the workspace grouping model with a flat nine-module navigation shell. Reuse existing market, sector, stock, portfolio, report, and channel logic; add lightweight derived renderers for limit-up and limit-down views.

**Tech Stack:** Python 3.11+, standard library HTTP server, existing `stock_ts.web` and `stock_ts.webapp` modules, pytest, ruff.

---

### Task 1: Lock the new navigation contract with tests

**Files:**
- Modify: `tests/test_web_app_shell.py`
- Modify: `tests/test_web_layout.py`
- Modify: `tests/test_web_data_sources.py`

- [ ] Add failing assertions for the nine sidebar labels and new module ids/content.
- [ ] Run targeted tests and confirm failure.
- [ ] Keep failures specific to the new shell contract.

### Task 2: Flatten the web shell from workspaces to nine modules

**Files:**
- Modify: `src/stock_ts/webapp/composition.py`
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/workspaces.py`

- [ ] Replace the four-workspace grouping with nine flat module entries.
- [ ] Keep hash routing simple: one nav item -> one module.
- [ ] Remove or neutralize panel-tab logic that only existed for grouped workspaces.

### Task 3: Re-map page sections to the new business modules

**Files:**
- Modify: `src/stock_ts/web.py`

- [ ] Remove old conceptual modules from the active shell mapping.
- [ ] Rename candidates presentation to “智能选股”.
- [ ] Rename status presentation to “消息渠道”.
- [ ] Ensure daily report is exposed as a first-class visible module.

### Task 4: Add涨停板 and 跌停板 derived modules

**Files:**
- Modify: `src/stock_ts/web.py`
- Optional helper extraction if needed: `src/stock_ts/webapp/view_models.py`

- [ ] Build a lightweight derived list from candidate-universe style data using latest pct change.
- [ ] Render a “涨停板” module with count, strongest symbols, and source caveat.
- [ ] Render a “跌停板” module with count, weakest symbols, and risk notes.
- [ ] Keep the logic deterministic and dependency-free.

### Task 5: Polish module copy and preserve core actions

**Files:**
- Modify: `src/stock_ts/web.py`
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `README.md`

- [ ] Remove non-professional module wording.
- [ ] Keep toolbar, stock lookup, holdings edit, and channel send actions intact.
- [ ] Make the shell read like mature software: fewer concepts, clearer labels.

### Task 6: Verify the full path

**Files:**
- Modify if needed based on failures

- [ ] Run targeted pytest for web shell and channel pages.
- [ ] Run full `pytest -q`.
- [ ] Run `make lint`.
- [ ] Start the local server and verify the new module labels render in served HTML.
