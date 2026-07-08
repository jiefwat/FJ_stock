# Structured Daily Decisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a structured `reports/daily/latest_decisions.json` artifact and make the morning email prefer it over Markdown parsing.

**Architecture:** Add a focused decision artifact module that turns the existing generated Markdown into a compact JSON contract. The daily pipeline writes the JSON next to `latest.md`; `send_morning_report.py` reads it first for traffic-light holdings and opportunities, falling back to Markdown parsing when missing.

**Tech Stack:** Python 3.11, dataclasses-free JSON helpers, pytest, existing `scripts/run_daily_analysis.py` and `scripts/send_morning_report.py`.

---

### Task 1: Decision Artifact Contract

**Files:**
- Create: `src/stock_ts/daily_decisions.py`
- Test: `tests/test_daily_decisions.py`

- [ ] Write a failing test that passes sample Markdown containing market summary, weak holdings, detailed holdings, and candidates to `build_decision_artifact(markdown, pipeline_status="...")` and asserts the output has `market`, `traffic_lights.red`, `traffic_lights.yellow`, `traffic_lights.green`, `opportunities`, and `data_limits`.
- [ ] Run `PYTHONPATH=src .venv/bin/python -m pytest tests/test_daily_decisions.py -q` and confirm it fails because the module does not exist.
- [ ] Implement `build_decision_artifact`, `write_decision_artifact`, and `read_decision_artifact` with a stable dictionary shape and safe empty fallbacks.
- [ ] Re-run the test and confirm it passes.

### Task 2: Daily Analysis Writes JSON

**Files:**
- Modify: `scripts/run_daily_analysis.py`
- Test: existing/new test around daily artifact writing if available; otherwise add focused test in `tests/test_daily_decisions.py` for `write_decision_artifact`.

- [ ] Find where `reports/daily/latest.md` is written.
- [ ] After the Markdown report is written, call `write_decision_artifact(report_text, latest_decisions_path, pipeline_status=...)`.
- [ ] Ensure JSON is written to `reports/daily/latest_decisions.json` and date archive can be added later without blocking this change.

### Task 3: Morning Report Uses JSON First

**Files:**
- Modify: `scripts/send_morning_report.py`
- Test: `tests/test_send_morning_report.py`

- [ ] Add a failing test that creates `latest_decisions.json` with red/yellow/green/opportunities but no useful Markdown holding details; assert the morning report uses JSON names and actions.
- [ ] Implement JSON loading from `daily_dir/latest_decisions.json`.
- [ ] Make `## 红黄绿交易清单` and `## 今日机会 10 条` prefer structured JSON, then fall back to existing Markdown helpers.
- [ ] Keep all existing tests passing.

### Task 4: Verify and Deploy

**Files:**
- No code files unless tests reveal issues.

- [ ] Run `make lint`.
- [ ] Run `PYTHONPATH=src .venv/bin/python -m pytest --ignore=tests/test_docs_file_center_app.py -q`.
- [ ] Commit and push.
- [ ] Rsync to `/opt/stock-ts`, restart `stock-ts.service`, check local and public `/healthz`.
- [ ] On the server, build a morning report preview and confirm it reads `latest_decisions.json` if present.
