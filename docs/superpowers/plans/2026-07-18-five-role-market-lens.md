# StockTS Five-Role Market Lens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the report-shaped first screen with a structurally distinct Market Lens decision workspace while preserving every analysis, snapshot, API, privacy, and routing contract.

**Architecture:** Refactor only the server-rendered shell and workspace composition. Project validated bootstrap payload core fields into HTML, retain all existing data hooks and JavaScript hydration, and restyle the existing final visual authority instead of adding another skin.

**Tech Stack:** Python server-rendered HTML, vanilla JavaScript, CSS, pytest, BeautifulSoup.

---

### Task 1: Lock Structural Contracts

**Files:**
- Modify: `tests/test_web_design_guide_shell.py`
- Modify: `tests/test_web_native_research_workspaces.py`

- [x] Add failing tests asserting a command-bar stock search, an integrated decision board, findings inside judgment, stock deep research after the decision board, a closed deep-research disclosure, and server-rendered initial verdict/action/risk.
- [x] Run the focused tests and confirm failure is caused by the old DOM.

### Task 2: Refactor Shell And Workspace DOM

**Files:**
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`

- [x] Move the desktop stock search to `workspace-command-bar` while preserving the existing form contract.
- [x] Reorder sidebar source DOM to brand, navigation, account; keep stock search in the desktop command bar only.
- [x] Add escaped initial-payload projection for decision label, verdict, action, risk, evidence time, coverage, and three findings.
- [x] Move findings into `engine-judgment`, remove visual reliance on shortcut buttons, and place stock deep research after primary content in source order.
- [x] Convert stock deep research to a closed `details` disclosure without changing its data hooks or request behavior.
- [x] Set a real evidence-scale percentage during `renderEngineResult()` hydration.

### Task 3: Build The Market Lens Visual Authority

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`

- [x] Change the final skin to a 184px rail and 60px command/search bar.
- [x] Hide duplicated protocol/header status surfaces while retaining their DOM hooks.
- [x] Build a dark 12-column decision board with thesis/reasons on the left and action/invalidation on the right.
- [x] Style the real coverage scale, compact primary tables, bottom account surface, and closed research disclosure.
- [x] Preserve desktop local scrolling and declare a 1180px minimum application width.

### Task 4: Verify And Deploy

**Files:**
- Modify only if verification identifies a scoped regression.

- [x] Run `make lint`, the native visual/workspace suite, the professional workbench quality gate, and `git diff --check`.
- [x] Inspect authenticated 1440x900 and 1680x1050 layouts; verify no waiting flash for validated snapshot pages, no overflow, and no console errors.
- [ ] Commit and push only the scoped source, tests, spec, and plan; leave `data/research/` untouched.
- [ ] Create a production rollback bundle, fast-forward `/opt/stock-ts`, restart only `stock-ts.service`, and verify health, timers, pipeline status, and deployed commit equality.
