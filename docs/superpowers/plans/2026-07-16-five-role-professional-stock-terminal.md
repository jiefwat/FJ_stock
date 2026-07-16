# Five-Role Professional Stock Terminal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make StockTS conclusions time-honest, separate market facts from opportunity forecasts, and differentiate the four desktop research tasks without changing provider or account behavior.

**Architecture:** Preserve `ResearchWorkspaceResult` as the supplier-neutral product contract. Tighten snapshot freshness and local semantic builders, then render a module-specific plain-language protocol line in the existing native workspace shell.

**Tech Stack:** Python 3.11+, dataclasses, pytest, server-rendered HTML, vanilla JavaScript and CSS.

---

### Task 1: Fact-date freshness

**Files:**
- Modify: `src/stock_ts/research_snapshots.py`
- Test: `tests/test_research_snapshots.py`

- [ ] Add a test saving `generated_at=now` with an old `as_of` and assert normal load rejects it while `allow_stale=True` returns `stale=True`.
- [ ] Run the test and verify it fails because `_payload_datetime()` prefers `generated_at`.
- [ ] Split archive timestamp from freshness timestamp; save archives by generation time and load freshness by `as_of` first.
- [ ] Run snapshot and delivery tests and verify they pass.

### Task 2: Market facts and opportunity semantics

**Files:**
- Modify: `src/stock_ts/research_fallback.py`
- Test: `tests/test_research_fallback.py`

- [ ] Add failing tests proving market public text excludes risk budget, position, candidate and buy/sell wording.
- [ ] Add a failing test proving opportunity output never contains `可进入投资候选`.
- [ ] Add a failing test proving news/announcement presence does not increase positive evidence count.
- [ ] Change market labels to descriptive breadth states, remove future confirmation fields from market movers, and rename the opportunity stage to `价格延续观察`.
- [ ] Count only positive structured fields as positive evidence and run the fallback suite.

### Task 3: Task-specific session line and compact desktop hierarchy

**Files:**
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_native_research_workspaces.py`
- Test: `tests/test_web_design_guide_shell.py`

- [ ] Add failing HTML/JS/CSS contract tests for four user questions, four horizons, dynamic data time/coverage and the absence of the redundant risk jump.
- [ ] Render the supplier-neutral session line and update it from `payload.as_of` and `payload.coverage`.
- [ ] Replace technical first-screen copy with plain Chinese and compact desktop title/verdict spacing.
- [ ] Keep mobile overflow, focus-visible and reduced-motion contracts green.

### Task 4: Verification and deployment

**Files:**
- Verify only; do not modify production data or secrets.

- [ ] Run `make lint`.
- [ ] Run the professional analytics, fallback, delivery, snapshot, native workspace, API, auth and timer suites.
- [ ] Run local HTTP and 1440/1680 desktop browser checks.
- [ ] Commit and push `codex/research-data-depth-v2`.
- [ ] Fast-forward `/opt/stock-ts`, restart only `stock-ts.service`, and verify `/healthz`, login, deployed commit, timer schedules and pipeline status.
