# StockTS UI Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the StockTS Web UI so it is faster-feeling, less repetitive, and clearer per module.

**Architecture:** Keep the existing server-rendered Python HTML architecture and the `webapp` shell split. Make focused shell/style changes first, then apply small Web rendering changes only where they reduce clutter without changing analysis logic.

**Tech Stack:** Python 3.11, stdlib HTML rendering, CSS embedded through `src/stock_ts/webapp/styles.py`, lightweight JavaScript in `src/stock_ts/webapp/shell.py`, pytest/ruff via Makefile.

---

### Task 1: Compact Shell

**Files:**
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/styles.py`

- [ ] **Step 1: Simplify sidebar context**

Remove the repeated sidebar description card and keep a short operation note. Sidebar should remain the module switcher.

- [ ] **Step 2: Replace hero topbar with compact desk bar**

Change `render_topbar` to output a compact bar with current module label, short description, and condensed status cards. Do not repeat the brand headline.

- [ ] **Step 3: Combine toolbar rhythm**

Keep the existing form fields, but style it as a compact command strip below or beside the module context.

- [ ] **Step 4: Remove slow-feeling scroll behavior**

Change JavaScript `scrollIntoView({ behavior: 'smooth' })` to instant scrolling or remove scroll when switching workspaces.

### Task 2: Visual Simplification

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`

- [ ] **Step 1: Reduce vertical weight**

Shrink module padding, topbar margins, large cards, and shadows.

- [ ] **Step 2: Make active workspace transition lighter**

Remove reveal animation for workspace panes unless reduced motion is off and animation is very short.

- [ ] **Step 3: Improve first-screen density**

Make global summary and current session cards more compact, with fewer competing blocks.

### Task 3: Module Focus

**Files:**
- Modify: `src/stock_ts/web.py`

- [ ] **Step 1: Add focus copy map**

Add a small helper that maps module ids to a single focus sentence when module headers render.

- [ ] **Step 2: Shorten global summary**

Reduce `_render_global_summary_strip` to one primary summary card and one current-session card.

- [ ] **Step 3: Fold secondary detail**

Where modules already have dense supporting blocks, use the existing `<details class="detail-shell">` pattern for lower-priority material without changing data calculations.

### Task 4: Verification

**Files:**
- No production file changes expected.

- [ ] **Step 1: Static checks**

Run `make lint` and fix any failures caused by the edits.

- [ ] **Step 2: Tests**

Run `make test` and fix any failures caused by the edits.

- [ ] **Step 3: Local smoke test**

Start the local app and verify all workspace links switch modules. Do not deploy.
