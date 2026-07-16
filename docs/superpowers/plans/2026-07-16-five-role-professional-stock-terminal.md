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

- [x] Add a test saving `generated_at=now` with an old `as_of` and assert normal load rejects it while `allow_stale=True` returns `stale=True`.
- [x] Run the test and verify it fails because `_payload_datetime()` prefers `generated_at`.
- [x] Split archive timestamp from freshness timestamp; save archives by generation time and load freshness by `as_of` first.
- [x] Run snapshot and delivery tests and verify they pass.

### Task 2: Market facts and opportunity semantics

**Files:**
- Modify: `src/stock_ts/research_fallback.py`
- Test: `tests/test_research_fallback.py`

- [x] Add failing tests proving market public text excludes risk budget, position, candidate and buy/sell wording.
- [x] Add a failing test proving opportunity output never contains `可进入投资候选`.
- [x] Add a failing test proving news/announcement presence does not increase positive evidence count.
- [x] Change market labels to descriptive breadth states, remove future confirmation fields from market movers, and rename the opportunity stage to `价格延续观察`.
- [x] Count only positive structured fields as positive evidence and run the fallback suite.

### Task 3: Task-specific session line and compact desktop hierarchy

**Files:**
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_native_research_workspaces.py`
- Test: `tests/test_web_design_guide_shell.py`

- [x] Add failing HTML/JS/CSS contract tests for four user questions, four horizons, dynamic data time/coverage and the absence of the redundant risk jump.
- [x] Render the supplier-neutral session line and update it from `payload.as_of` and `payload.coverage`.
- [x] Replace technical first-screen copy with plain Chinese and compact desktop title/verdict spacing.
- [x] Keep mobile overflow, focus-visible and reduced-motion contracts green.

### Task 4: Prediction feedback sample gate

**Files:**
- Modify: `src/stock_ts/prediction_feedback.py`
- Modify: `scripts/send_morning_report.py`
- Test: `tests/test_prediction_feedback.py`
- Test: `tests/test_send_morning_report.py`

- [x] Add failing tests proving fewer than 20 evaluated samples never displays a hit rate, average excess return or MAE.
- [x] Render `样本积累中 N/20，暂不评价命中率` in the workspace and morning report until the calibration threshold is reached.
- [x] Keep the existing full metrics for 20 or more evaluated samples.
- [x] Run prediction feedback and morning report tests.

### Task 5: Verification and deployment

**Files:**
- Verify only; do not modify production data or secrets.

- [x] Run `make lint`.
- [x] Run the professional analytics, fallback, delivery, snapshot, native workspace, API, auth and timer suites.
- [x] Run local HTTP and 1440/1680 desktop browser checks.
- [ ] Commit and push `codex/research-data-depth-v2`.
- [ ] Fast-forward `/opt/stock-ts`, restart only `stock-ts.service`, and verify `/healthz`, login, deployed commit, timer schedules and pipeline status.
