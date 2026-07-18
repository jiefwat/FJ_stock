# StockTS Modern Decision Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the report-like final visual layer with a modern desktop investment cockpit while preserving all StockTS behavior and data contracts.

**Architecture:** Add one final authoritative CSS layer in `styles.py`, leaving prior compatibility styles and all HTML/JavaScript behavior intact. Use CSS ordering to move stock judgment ahead of deep research, and lock the result with source-level visual contract tests.

**Tech Stack:** Python, server-rendered HTML, vanilla JavaScript, CSS, pytest, BeautifulSoup.

---

### Task 1: Lock The Modern Visual Contract

**Files:**
- Modify: `tests/test_web_design_guide_shell.py`

- [ ] **Step 1: Write the failing contract test**

Add a test that extracts the final `StockTS modern decision cockpit skin` layer and asserts normal-width fonts, a non-grid body background, 12px-or-larger primary radii, and stock judgment ordering before deep research.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest -q tests/test_web_design_guide_shell.py -k modern_decision_cockpit`

Expected: FAIL because the final skin marker does not exist yet.

### Task 2: Implement The Final Visual Layer

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`

- [ ] **Step 1: Add the final design tokens and app-frame overrides**

Define the cool mist, white, ocean, ink, muted, line, copper, positive, and warning tokens; use normal-width local font stacks; remove the final body grid; soften the sidebar and session bar; and preserve desktop viewport scrolling.

- [ ] **Step 2: Restyle the decision hierarchy and dense content**

Apply consistent card geometry, type scale, buttons, inputs, lists, tables, and evidence surfaces. Keep data fields tabular and retain semantic state colors.

- [ ] **Step 3: Reorder the stock workspace visually**

Make the stock module a flex column, assign explicit order values to all direct children, place the judgment before action shortcuts/findings, and place deep research after findings.

- [ ] **Step 4: Preserve the mobile contract**

At 760px and below, restore normal document scrolling; at 640px and below, use one-column decision content, full-width controls, and the existing mobile dock.

- [ ] **Step 5: Run the focused tests**

Run: `PYTHONPATH=src python3 -m pytest -q tests/test_web_design_guide_shell.py tests/test_web_native_research_workspaces.py`

Expected: PASS.

### Task 3: Verify And Deploy

**Files:**
- Modify: `docs/superpowers/specs/2026-07-16-stockts-visual-system-design.md`
- Create: `docs/superpowers/plans/2026-07-18-stockts-modern-decision-cockpit.md`

- [ ] **Step 1: Run repository quality gates**

Run: `make lint`, the professional-workbench test target if present, and `git diff --check`.

Expected: all commands exit 0.

- [ ] **Step 2: Verify browser layouts**

Inspect 1440x900, 1680x1050, and 390x844. Confirm decision-first ordering, working module navigation/refresh, no console errors, and no horizontal overflow.

- [ ] **Step 3: Commit the scoped change**

Stage only the spec, plan, test, and stylesheet. Exclude `data/research/`.

Commit: `[界面视觉] 重塑现代投资决策舱`

- [ ] **Step 4: Deploy through a complete Git bundle**

Back up the current server revision, fast-forward `/opt/stock-ts`, and restart only `stock-ts.service`. Do not run market pipelines, research jobs, or morning-report jobs.

- [ ] **Step 5: Verify public state**

Confirm server HEAD equals local HEAD, `/healthz` returns 200, `stock-ts.service` and the three schedule timers are active, the latest pipeline status is `ok`, and the public root preserves its expected authentication boundary.
