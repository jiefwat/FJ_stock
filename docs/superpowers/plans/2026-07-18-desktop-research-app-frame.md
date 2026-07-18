# Desktop Research App Frame Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing StockTS research page into a desktop application frame with persistent session context and workspace-local scrolling, without changing research data or module behavior.

**Architecture:** Add one provider-neutral session bar to the native shell, let the existing engine script synchronize it with the active workspace, and use a final authoritative CSS layer to make the desktop shell viewport-scoped. Below 760px, preserve the existing document scroll and mobile dock.

**Tech Stack:** Python HTML renderers, vanilla JavaScript, CSS, pytest, BeautifulSoup.

---

### Task 1: Lock the app-frame contract

**Files:**
- Modify: `tests/test_web_design_guide_shell.py`

- [ ] **Step 1: Write the failing rendered-HTML test**

Assert that the native page contains `data-workspace-command-bar`, `current-module-label`, target/delivery/time fields, and a `data-workspace-command-refresh` button.

- [ ] **Step 2: Write the failing CSS contract test**

Assert that the final skin contains a 58px command row, `height:100vh`, a `.workspace-stage`, independently scrolling active panes, a 1420px content limit, and mobile resets for page scrolling.

- [ ] **Step 3: Run the focused tests and verify RED**

Run: `python -m pytest -q tests/test_web_design_guide_shell.py -k "app_frame or session_bar"`

Expected: FAIL because the session bar and viewport CSS do not exist.

### Task 2: Render and synchronize the research session bar

**Files:**
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/__init__.py`
- Modify: `src/stock_ts/web.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`

- [ ] **Step 1: Render the session bar before the workspace stage**

Expose module, research target, delivery state, evidence time, and one refresh control using stable `data-*` hooks. Wrap the existing pane output in `.workspace-stage` without changing pane IDs or hash routes.

- [ ] **Step 2: Synchronize state from the active engine workspace**

Update the bar on module activation, loading, result rendering, and refresh completion. Derive targets only from the existing privacy-safe engine context.

- [ ] **Step 3: Delegate refresh to the active module**

Bind the session refresh control to `runEngineWorkspace(activeWorkspace, true)` and disable it for non-engine or unavailable workspaces.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `python -m pytest -q tests/test_web_design_guide_shell.py -k "app_frame or session_bar"`

Expected: PASS.

### Task 3: Apply the desktop viewport layout

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_design_guide_shell.py`

- [ ] **Step 1: Add the authoritative app-frame CSS**

At desktop widths, lock the shell to `100vh`, use a 58px command row plus a flexible workspace stage, scroll only `.workspace-pane.active`, and cap the content canvas at 1420px.

- [ ] **Step 2: Preserve responsive behavior**

At 760px and below, restore body and workspace document scrolling, make the command bar compact, and keep the existing bottom dock and overflow guards.

- [ ] **Step 3: Run visual and workspace regression tests**

Run: `python -m pytest -q tests/test_web_design_guide_shell.py tests/test_web_native_research_workspaces.py`

Expected: PASS.

### Task 4: Verify and deliver

**Files:**
- Modify only if verification finds a regression in the files above.

- [ ] **Step 1: Inspect 1440x900 and 1680x1050**

Verify module switching, local pane scrolling, fixed session context, refresh delegation, no horizontal overflow, and no console errors.

- [ ] **Step 2: Verify mobile compatibility**

Inspect 390px width for normal document scrolling, accessible controls, and an unobstructed mobile dock.

- [ ] **Step 3: Run repository quality gates**

Run: `make lint`, `git diff --check`, and the focused regression suite.

- [ ] **Step 4: Commit, push, deploy, and verify**

Push `codex/research-data-depth-v2`, deploy the verified bundle to `/opt/stock-ts`, restart only `stock-ts.service`, and verify the public health endpoint plus deployed commit identity.
