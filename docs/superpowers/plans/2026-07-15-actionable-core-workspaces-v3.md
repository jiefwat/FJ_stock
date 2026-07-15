# Actionable Core Workspaces V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the four native StockTs workspaces informative and operable without restoring the legacy long page.

**Architecture:** Enrich the deterministic local result protocol with market movers, holding decisions, and a stock decision record. Render private holdings management server-side, while rendering public research results with safe DOM construction and a single opportunity list.

**Tech Stack:** Python 3.12, dataclasses, stdlib HTTP server, vanilla JavaScript, CSS, pytest, ruff.

---

### Task 1: Lock The Research Contracts

**Files:**
- Modify: `tests/test_research_fallback.py`
- Modify: `tests/test_web_native_research_workspaces.py`

- [ ] Add a failing market test requiring `market-movers` items with move, reason,
  confirmation, and invalidation facts.
- [ ] Add a failing portfolio test requiring action, reason, trigger, and invalidation
  facts on every holding item.
- [ ] Add a failing stock test requiring `stock-decision` before `stock-evidence`.
- [ ] Add a failing opportunity test requiring one reasoned candidate section and no
  separately rendered opportunity module-item list.
- [ ] Run the focused tests and confirm the failures describe the missing contracts.

### Task 2: Enrich Deterministic Local Research

**Files:**
- Modify: `src/stock_ts/research_fallback.py`
- Test: `tests/test_research_fallback.py`

- [ ] Analyze the full candidate scan once and build the abnormal-move/watch list.
- [ ] Add structured facts to market movers, holdings, and opportunity candidates.
- [ ] Add the stock decision record before the evidence matrix.
- [ ] Replace candidate findings with theme, coverage, and exclusion-rule findings.
- [ ] Run `python3 -m pytest -q tests/test_research_fallback.py` and confirm green.
- [ ] Commit the deterministic research changes.

### Task 3: Restore Native Operations

**Files:**
- Modify: `src/stock_ts/web.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_native_research_workspaces.py`
- Test: `tests/test_web_auth.py`

- [ ] Render the authenticated holdings manager with existing add/edit/delete handlers.
- [ ] Pass edit code and provider context into the native page without exposing another
  user's holdings path.
- [ ] Render the stock switcher and full-market entry.
- [ ] Render market movers and portfolio drill-down links.
- [ ] Replace grouped opportunity cards with one responsive reasoned list and suppress
  the duplicate `module_items` surface for opportunity.
- [ ] Run native UI and authentication tests and confirm green.
- [ ] Commit the native workspace changes.

### Task 4: Verify And Deploy

**Files:**
- No source changes expected.

- [ ] Run `git diff --check`, `make lint`, and the professional/auth/snapshot/systemd
  focused suite.
- [ ] Run the full suite and compare any failures with the recorded `d874781` baseline.
- [ ] Browser-test authenticated market, portfolio edit controls, holding drill-down,
  stock switcher, overall stock decision, and the single opportunity list at 1440,
  1280, and 390 widths.
- [ ] Confirm the console is clean and provider terms are absent.
- [ ] Create a timestamped production backup, deploy the tested commit, and restart only
  `stock-ts.service`.
- [ ] Verify public health/login, authenticated four-workspace behavior, holdings write
  round-trip using the existing owner account without changing holdings, and all three
  existing timers.
