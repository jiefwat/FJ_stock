# Market Facts, Opportunity Forecast, and Morning Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate factual market reporting from forward opportunity research, add theme and stock drill-down, produce a gated Top10 with automatic/user feedback, align the morning brief, and deploy four daily Beijing-time refreshes.

**Architecture:** Keep market facts and opportunity forecasts in the existing provider-neutral `ResearchWorkspaceResult` contract. Add a focused SQLite prediction ledger that records immutable T0 predictions, evaluates T+1/T+3/T+5/T+10 outcomes from local snapshot bars, and exposes aggregate feedback without account data. Reuse the existing web service, daily research task, morning-report sender, and `stock-ts-daily-analysis.timer`; do not add a service or user-facing provider dependency.

**Tech Stack:** Python 3.11, standard-library `sqlite3`, dataclasses, stdlib HTTP server, existing HTML/JavaScript workspace, pytest, ruff, systemd.

---

## File Structure

- Create `src/stock_ts/prediction_feedback.py`: immutable prediction/outcome/user-feedback store, outcome evaluator, and public aggregate payload.
- Create `tests/test_prediction_feedback.py`: ledger idempotency, immutability, horizon evaluation, calibration, and account-feedback isolation.
- Modify `src/stock_ts/research_fallback.py`: remove forecasts from market, gate opportunity Top10, filter by selected theme, and attach deterministic prediction ids.
- Modify `src/stock_ts/web.py`: pass `theme` and `source_theme` through the native page, avoid global snapshots for theme requests, expose account-bound feedback POST, and append aggregate feedback.
- Modify `src/stock_ts/webapp/engine_workspace.py`: render clickable themes, source-theme context, candidate stock links, and compact feedback.
- Modify `src/stock_ts/webapp/styles.py`: selected-theme, feedback-summary, and mobile list styles.
- Modify `scripts/run_daily_research.py`: evaluate due predictions, persist current close-qualified opportunities, and write feedback summary.
- Modify `scripts/run_daily_pipeline.py`: record refresh-session metadata and distinguish morning, pre-open, intraday, close, and manual runs.
- Modify `scripts/send_morning_report.py`: render five fixed sections from structured facts, holdings, opportunities, feedback, and blockers.
- Modify `deploy/systemd/stock-ts-daily-analysis.timer`: schedule `07:00/09:00/13:00/15:00` in the server's `Asia/Shanghai` timezone.
- Modify focused tests under `tests/` to protect the new contracts and existing auth/holdings behavior.

### Task 1: Market Facts and Gated Opportunity Top10

**Files:**
- Modify: `src/stock_ts/research_fallback.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_research_fallback.py`
- Test: `tests/test_web_research_workspace_api.py`

- [ ] **Step 1: Write failing market/opportunity contract tests**

Add tests that require market sections to be facts only and opportunity candidates to contain only close-qualified continuation stages:

```python
def test_market_contains_facts_but_no_forecast_watchlist() -> None:
    result = build_local_research("market", ResearchContext(), provider=MultiDayCandidateProvider())
    keys = {section.key for section in result.module_sections}
    assert "market-breadth" in keys
    assert "market-themes" in keys
    assert "market-movers" in keys
    assert "market-continuation" not in keys
    assert "未来" not in result.action
    assert "候选" not in result.action


def test_opportunity_top10_contains_only_investable_continuation_stages() -> None:
    result = build_local_research(
        "opportunity",
        ResearchContext(),
        provider=MultiDayCandidateProvider(),
    )
    section = next(item for item in result.module_sections if item.key == "opportunity-candidates")
    assert len(section.items) <= 10
    stages = {
        next(fact.value for fact in item.facts if fact.label == "阶段判断")
        for item in section.items
    }
    assert stages <= {"可进入投资候选", "等待确认"}
    assert all(item.status == "ready" for item in section.items)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_research_fallback.py::test_market_contains_facts_but_no_forecast_watchlist \
  tests/test_research_fallback.py::test_opportunity_top10_contains_only_investable_continuation_stages
```

Expected: market still contains `market-continuation`; opportunity stages still expose raw continuation labels.

- [ ] **Step 3: Implement the fact/forecast boundary**

In `_build_market_research`, remove candidate ranking and `market-continuation`. Keep observed index, breadth, theme, pulse, and mover sections. Set the action to a navigation boundary rather than an investment instruction:

```python
action="这里只记录已发生的市场事实；未来机会与确认条件请进入热门机会。"
```

In `_build_opportunity_research`, accept `selected_theme: str = ""`, filter by normalized theme, and map stages:

```python
FORWARD_STAGE = {
    "延续观察": "可进入投资候选",
    "突破待确认": "等待确认",
}

eligible = [
    row for row in _rank_continuation_candidates(...)
    if row[2].stage in FORWARD_STAGE
    and (not selected_theme or _same_theme(row[0].sector, selected_theme))
]
candidate_items = tuple(
    _continuation_candidate_item(
        raw,
        profile,
        assessment,
        kind="candidate",
        public_stage=FORWARD_STAGE[assessment.stage],
    )
    for raw, profile, assessment in eligible[:10]
)
```

Pass `context.sector` from `build_local_research`. Update `_snapshot_supports_workspace` so market requires `market-pulse`, `market-breadth`, `market-themes`, and `market-movers`, not `market-continuation`.

- [ ] **Step 4: Run the tests and verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_research_fallback.py \
  tests/test_web_research_workspace_api.py
```

Expected: all tests pass with market facts and a non-padded opportunity Top10.

- [ ] **Step 5: Commit**

```bash
git add src/stock_ts/research_fallback.py src/stock_ts/web.py \
  tests/test_research_fallback.py tests/test_web_research_workspace_api.py
git commit -m "feat: separate market facts from opportunity forecasts"
```

### Task 2: Theme and Stock Drill-Down

**Files:**
- Modify: `src/stock_ts/web.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_module_decisions.py`
- Test: `tests/test_web_native_research_workspaces.py`

- [ ] **Step 1: Write failing route and UI tests**

```python
def test_native_page_passes_selected_theme_to_opportunity_workspace() -> None:
    html = render_page(stock_code="600519", provider_name="sample", selected_theme="半导体")
    assert 'data-engine-context="{&quot;sector&quot;:&quot;半导体&quot;}"' in html
    assert "正在查看主题：半导体" in html


def test_engine_theme_and_candidate_links_preserve_context() -> None:
    script = engine_app_script()
    assert "/?theme=${encodeURIComponent" in script
    assert "source_theme=${encodeURIComponent" in script
    assert "candidate_source=opportunity" in script
```

Add a handler test for `/?theme=半导体#opportunity` and `/?code=688981&source_theme=半导体#stock`.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_web_native_research_workspaces.py \
  tests/test_web_module_decisions.py -k 'theme or candidate_source'
```

Expected: `render_page` has no selected-theme arguments and engine theme cards are not links.

- [ ] **Step 3: Pass safe route context through the native page**

Add `selected_theme` and `source_theme` arguments to `render_page` and `_render_native_research_page`. Parse them in `Handler.do_GET` with existing `_clean_iwencai_text` limits. Build contexts as follows:

```python
"stock": render_engine_workspace(
    "stock",
    status=service_status,
    context={**stock_context, "source_theme": source_theme},
),
"opportunity": render_engine_workspace(
    "opportunity",
    status=service_status,
    context={"sector": selected_theme} if selected_theme else {},
),
```

When an opportunity request has a sector, `_research_workspace_response` must bypass the global opportunity snapshot, build/filter the requested context, and not overwrite the global snapshot.

- [ ] **Step 4: Render clickable themes and contextual stock links**

Change `renderEngineThemeSection` to create an anchor with:

```javascript
link.href = `/?theme=${encodeURIComponent(item.name || '')}#opportunity`;
```

Change `engineStockAnalysisLink` to read the row theme and create:

```javascript
link.href = `/?code=${encodeURIComponent(item.code || '')}`
  + `&source_theme=${encodeURIComponent(item.label || '')}`
  + `&candidate_source=opportunity#stock`;
```

Render a selected-theme banner with “返回全部主题”. Render a stock source banner only when `source_theme` is non-empty. Use `textContent`/escaped server HTML only.

- [ ] **Step 5: Run tests and verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_web_native_research_workspaces.py \
  tests/test_web_module_decisions.py \
  tests/test_web_design_guide_shell.py
```

Expected: route, context, navigation, and existing shell tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/stock_ts/web.py src/stock_ts/webapp/engine_workspace.py \
  src/stock_ts/webapp/styles.py tests/test_web_native_research_workspaces.py \
  tests/test_web_module_decisions.py tests/test_web_design_guide_shell.py
git commit -m "feat: add opportunity theme drill-down"
```

### Task 3: Immutable Prediction Ledger and Outcome Evaluation

**Files:**
- Create: `src/stock_ts/prediction_feedback.py`
- Create: `tests/test_prediction_feedback.py`

- [ ] **Step 1: Write failing ledger tests**

Cover deterministic ids, duplicate writes, immutable T0 fields, T+1/T+3/T+5/T+10 outcomes, MFE/MAE, benchmark excess return, missing bars, and account-isolated user feedback:

```python
def test_prediction_is_idempotent_and_original_thesis_is_immutable(tmp_path: Path) -> None:
    store = PredictionStore(tmp_path / "predictions.sqlite3")
    prediction = PredictionInput(
        baseline_trade_date="2026-07-15",
        baseline_price=100.0,
        subject_code="600001",
        subject_name="稳步上行",
        theme="半导体",
        stage="可进入投资候选",
        score=82,
        confidence="中",
        support="多周期趋势同向",
        counter_evidence="波动仍高",
        confirmation="量能保持",
        invalidation="跌破十日线",
        data_as_of="2026-07-15",
        evidence_as_of="2026-07-15",
    )
    first = store.record(prediction)
    second = store.record(replace(prediction, support="事后改写"))
    assert first == second
    assert store.get(first).support == "多周期趋势同向"


def test_evaluate_due_horizons_records_returns_mfe_mae_and_excess(tmp_path: Path) -> None:
    store = seeded_store(tmp_path)
    store.evaluate(
        "600001",
        closes=[100, 103, 101, 106, 108, 109, 110, 111, 112, 113, 114],
        benchmark_closes=[100, 101, 101, 102, 103, 103, 104, 104, 105, 105, 106],
    )
    outcomes = store.outcomes_for("600001")
    assert {row.horizon for row in outcomes} == {1, 3, 5, 10}
    assert outcomes[1].absolute_return == 3.0
    assert outcomes[3].excess_return == 4.0
    assert outcomes[5].mfe > 0
    assert outcomes[5].mae <= 0
```

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest -q tests/test_prediction_feedback.py`

Expected: import fails because `prediction_feedback.py` does not exist.

- [ ] **Step 3: Implement schema and immutable writes**

Create dataclasses `PredictionInput`, `PredictionRecord`, `PredictionOutcome`, and `PredictionSummary`. Initialize tables:

```sql
CREATE TABLE IF NOT EXISTS predictions (
  prediction_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  baseline_trade_date TEXT NOT NULL,
  baseline_price REAL NOT NULL,
  subject_code TEXT NOT NULL,
  subject_name TEXT NOT NULL,
  theme TEXT NOT NULL,
  stage TEXT NOT NULL,
  score INTEGER NOT NULL,
  confidence TEXT NOT NULL,
  support TEXT NOT NULL,
  counter_evidence TEXT NOT NULL,
  confirmation TEXT NOT NULL,
  invalidation TEXT NOT NULL,
  data_as_of TEXT NOT NULL,
  evidence_as_of TEXT NOT NULL,
  model_version TEXT NOT NULL,
  snapshot_fingerprint TEXT NOT NULL
);
```

Use `INSERT OR IGNORE`; derive `prediction_id` from SHA-256 of baseline date, code, model version, and snapshot fingerprint. Add `prediction_outcomes` with `(prediction_id, horizon)` primary key and `prediction_user_feedback` with `(prediction_id, user_id)` primary key.

- [ ] **Step 4: Implement outcome evaluation and summary**

Use trading-bar positions, not calendar-day offsets. For each due horizon calculate:

```python
absolute_return = (close_h / baseline_price - 1) * 100
benchmark_return = (benchmark_h / benchmark_baseline - 1) * 100
excess_return = absolute_return - benchmark_return
mfe = (max(highs[:horizon + 1]) / baseline_price - 1) * 100
mae = (min(lows[:horizon + 1]) / baseline_price - 1) * 100
```

Classify invalidated first, then hit when excess return is positive and MAE stays within the recorded invalidation rule proxy; otherwise miss/expired. Missing future bars stay pending and do not enter denominators. `summary(horizon=3)` returns sample count, hit rate, mean/median excess, mean MAE, calibration buckets, and top miss reason; below 20 samples sets `sample_state="样本积累中"`.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `PYTHONPATH=src .venv/bin/pytest -q tests/test_prediction_feedback.py`

Expected: all ledger tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/stock_ts/prediction_feedback.py tests/test_prediction_feedback.py
git commit -m "feat: add immutable opportunity prediction ledger"
```

### Task 4: Daily Research Integration and Feedback UI/API

**Files:**
- Modify: `scripts/run_daily_research.py`
- Modify: `src/stock_ts/web.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_daily_research.py`
- Modify: `tests/test_web_research_workspace_api.py`
- Modify: `tests/test_web_native_research_workspaces.py`

- [ ] **Step 1: Write failing integration tests**

Require daily research to evaluate old records before recording current candidates, write `feedback_summary.json`, and keep only one prediction per stable key. Require the opportunity API to append `opportunity-feedback`. Require user feedback to use the authenticated user id and never change score.

```python
def test_daily_research_records_predictions_and_writes_feedback(tmp_path: Path) -> None:
    result = run_daily_research(
        output_dir=tmp_path / "research",
        prediction_db=tmp_path / "predictions.sqlite3",
        snapshot_path=FIXTURE_SNAPSHOT,
        service=OpportunityFixtureService(),
        now=NOW,
    )
    assert result.ok
    summary = json.loads((tmp_path / "research/feedback_summary.json").read_text())
    assert summary["horizon"] == 3
    assert PredictionStore(tmp_path / "predictions.sqlite3").count() == 2
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_daily_research.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_native_research_workspaces.py
```

Expected: daily research has no prediction arguments or feedback section.

- [ ] **Step 3: Integrate the ledger into daily research**

Add CLI defaults:

```text
--snapshot data/imports/tdx_snapshots.json
--prediction-db data/research/predictions.sqlite3
--feedback-summary reports/research/feedback_summary.json
```

Load bars from the local snapshot, evaluate due predictions, research market/opportunity, extract `opportunity-candidates`, record only `可进入投资候选`/`等待确认` rows with reliable same-date baseline prices, then atomically write the 3-day summary. Store counts and errors in `daily.status.json`; ledger failures degrade status but do not delete research snapshots.

- [ ] **Step 4: Append feedback to opportunity responses**

Add `opportunity_feedback_section(store.summary(3))` returning public payload:

```python
{
    "key": "opportunity-feedback",
    "title": "历史预测反馈",
    "conclusion": "样本积累中" if summary.sample_count < 20 else "近20次校准结果",
    "tone": "neutral",
    "items": [...],
}
```

Append this section to live, snapshot, stale-snapshot, and local opportunity responses. Never include DB paths or provider fields.

- [ ] **Step 5: Add account-bound feedback endpoint and controls**

Handle `POST /api/predictions/feedback` only after existing login enforcement. Accept JSON `{prediction_id, usefulness, reason_accuracy, disposition}` with allowlisted values. Call:

```python
store.record_user_feedback(
    prediction_id=prediction_id,
    user_id=current_user.id,
    usefulness=usefulness,
    reason_accuracy=reason_accuracy,
    disposition=disposition,
)
```

Render compact “有用/没用” controls on opportunity rows only when a `预测编号` fact exists. Verify that the stored feedback does not alter prediction score or aggregate market outcomes.

- [ ] **Step 6: Run tests and verify GREEN**

Run the same tests from Step 2. Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/run_daily_research.py src/stock_ts/web.py \
  src/stock_ts/webapp/engine_workspace.py src/stock_ts/webapp/styles.py \
  tests/test_daily_research.py tests/test_web_research_workspace_api.py \
  tests/test_web_native_research_workspaces.py
git commit -m "feat: close the opportunity forecast feedback loop"
```

### Task 5: Five-Section Morning Brief

**Files:**
- Modify: `scripts/send_morning_report.py`
- Modify: `tests/test_send_morning_report.py`

- [ ] **Step 1: Write failing morning-brief tests**

Add a structured opportunity snapshot and feedback summary fixture, then assert exact section order and limits:

```python
assert headings == [
    "## 最新市场事实",
    "## 先处理持仓",
    "## 今日前瞻机会",
    "## 预测反馈",
    "## 数据风险",
]
assert len(_section_lines(content, "## 今日前瞻机会", "## 预测反馈")) <= 3
assert "样本积累中" in content
assert "候选4" not in content
assert "provider" not in content.lower()
assert "不构成投资建议" in content
```

Add tests for one candidate (no padding), no due samples, stale 07:00 status, theme/stock links, and dry-run send.

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest -q tests/test_send_morning_report.py`

Expected: old headings `30秒结论/今日只看3只/三条纪律/到公司再看` remain.

- [ ] **Step 3: Render five structured sections**

Add `research_dir="reports/research"` and `prediction_summary_path` defaults. Prefer:

1. `latest_decisions.json` and market research snapshot for latest facts.
2. account-specific holdings decisions for up to three actions.
3. `opportunity/latest.json` for up to three gated candidates.
4. `feedback_summary.json` for the 3-day calibration line.
5. `pipeline.status` and research status for at most two blockers.

Use links:

```python
theme_url = f"{site_url}/?{urlencode({'theme': theme})}#opportunity"
stock_url = f"{site_url}/?{urlencode({'code': code, 'source_theme': theme})}#stock"
```

Keep the single discipline and concise disclaimer. Do not include command output, paths, source branding, or more than three opportunity names.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `PYTHONPATH=src .venv/bin/pytest -q tests/test_send_morning_report.py`

Expected: all morning tests pass after updating obsolete copy assertions to the new five-section contract.

- [ ] **Step 5: Commit**

```bash
git add scripts/send_morning_report.py tests/test_send_morning_report.py
git commit -m "feat: align morning brief with forecast evidence"
```

### Task 6: Four Refresh Sessions and Pipeline Audit Metadata

**Files:**
- Modify: `deploy/systemd/stock-ts-daily-analysis.timer`
- Modify: `scripts/run_daily_pipeline.py`
- Modify: `tests/test_systemd_timer_contract.py`
- Modify: `tests/test_daily_pipeline.py`

- [ ] **Step 1: Write failing timer/session tests**

```python
def test_stock_ts_daily_timer_uses_four_beijing_refresh_windows() -> None:
    text = Path("deploy/systemd/stock-ts-daily-analysis.timer").read_text()
    assert text.count("OnCalendar=") == 4
    for checkpoint in ("07:00:00", "09:00:00", "13:00:00", "15:00:00"):
        assert f"OnCalendar=*-*-* {checkpoint}" in text
    assert "AccuracySec=1m" in text
    assert "00:00:00" not in text


@pytest.mark.parametrize(
    ("hour", "session", "intraday"),
    [(7, "morning", False), (9, "preopen", False), (13, "midday", True), (15, "close", False)],
)
def test_pipeline_status_records_refresh_session(tmp_path, hour, session, intraday):
    result = run_daily_pipeline(config, runner=fake_runner, now=NOW.replace(hour=hour))
    status = parse_status(result.status_path)
    assert status["session_name"] == session
    assert status["intraday"] == str(intraday).lower()
    assert status["scheduled_at"].endswith(f"{hour:02d}:00:00+08:00")
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_systemd_timer_contract.py \
  tests/test_daily_pipeline.py -k 'refresh_session or timer'
```

Expected: old timer includes midnight and pipeline status lacks session fields.

- [ ] **Step 3: Implement timer and status metadata**

Change the timer to four `OnCalendar` lines, `Persistent=true`, `AccuracySec=1m`. Add optional `now` to `run_daily_pipeline`; derive session with exact hour mapping and `manual` fallback. Write:

```text
scheduled_at
started_at
completed_at
session_name
intraday
market_trade_date
scanned_count
enriched_count
eligible_count
```

Preserve previous snapshot on failure. At `13:00`, mark status intraday and do not represent it as a complete close. At `15:00`, data-chain failure or an old market date remains failed/degraded instead of `ok`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_systemd_timer_contract.py tests/test_daily_pipeline.py
```

Expected: all timer and pipeline tests pass.

- [ ] **Step 5: Commit**

```bash
git add deploy/systemd/stock-ts-daily-analysis.timer scripts/run_daily_pipeline.py \
  tests/test_systemd_timer_contract.py tests/test_daily_pipeline.py
git commit -m "feat: refresh market data at four daily checkpoints"
```

### Task 7: Full Verification, Documentation, and Deployment

**Files:**
- Modify: `docs/TODO.md`
- Modify: `docs/agent-ops/README.md` if refresh commands or deployment steps change

- [ ] **Step 1: Run formatting and focused verification**

```bash
make lint
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_continuation.py \
  tests/test_research_fallback.py \
  tests/test_prediction_feedback.py \
  tests/test_daily_research.py \
  tests/test_daily_pipeline.py \
  tests/test_send_morning_report.py \
  tests/test_systemd_timer_contract.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_native_research_workspaces.py \
  tests/test_web_module_decisions.py \
  tests/test_web_design_guide_shell.py
```

Expected: lint and all focused tests pass.

- [ ] **Step 2: Run core and full regression suites**

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Compare failures against the established full-suite baseline. Investigate every new failure; do not classify a new failure as legacy without reproducing it on `e572aae`.

- [ ] **Step 3: Run local dry-runs and browser checks**

```bash
PYTHONPATH=src .venv/bin/python scripts/run_daily_research.py \
  --output-dir /tmp/stockts-research-verify \
  --prediction-db /tmp/stockts-predictions.sqlite3 \
  --snapshot data/imports/tdx_snapshots.json

PYTHONPATH=src .venv/bin/python scripts/send_morning_report.py --dry-run
```

Start the local web service and verify desktop and 390px mobile behavior for:

- market has facts and no continuation candidates;
- market theme opens filtered opportunity;
- candidate opens stock with source theme;
- Top10 never exceeds 10 and is not padded;
- feedback summary and feedback buttons work;
- no provider branding or horizontal overflow.

- [ ] **Step 4: Update docs and commit verified implementation**

Mark the completed work in `docs/TODO.md`, document four refresh sessions and prediction storage without secrets, then commit:

```bash
git add docs/TODO.md docs/agent-ops/README.md
git commit -m "docs: document forecast feedback operations"
```

- [ ] **Step 5: Deploy application code without overwriting runtime data**

Create a deployment archive from tracked files only. Exclude `.env`, `data/auth`, user holdings, snapshots, reports, SQLite prediction data, Nginx, and runtime secrets. Upload with:

```bash
scp -i ~/.ssh/stockts_aliyun_deploy -o IdentitiesOnly=yes \
  /tmp/stockts-deploy.tar.gz admin@47.82.145.207:/tmp/stockts-deploy.tar.gz
```

On the server, back up changed tracked files, extract into `/opt/stock-ts`, run compile/focused tests, and restart `stock-ts.service`.

- [ ] **Step 6: Deploy and reload the timer**

Install the tracked timer file at `/etc/systemd/system/stock-ts-daily-analysis.timer`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart stock-ts-daily-analysis.timer
systemctl list-timers stock-ts-daily-analysis.timer --all --no-pager
```

Verify the next run is one of `07:00/09:00/13:00/15:00 CST`, with four `OnCalendar` entries and no midnight run.

- [ ] **Step 7: Verify production**

Verify:

```bash
systemctl is-active stock-ts.service
systemctl is-active stock-ts-daily-analysis.timer
systemctl is-active stock-ts-daily-research.timer
systemctl is-active stock-ts-morning-email.timer
curl -fsS http://127.0.0.1:8501/healthz
curl -fsS https://stock.jiewat-kaka-fj.com/healthz
```

Use an authenticated production session to check market facts, theme drill-down, stock source context, feedback, and morning-report dry-run. Confirm production HTML/JSON contains no external provider branding, capability ids, trace ids, internal paths, or secrets.

- [ ] **Step 8: Record the deployed commit and final evidence**

Report the final commit, public URL, active timer schedule, focused/full test results, morning dry-run result, production service status, and any data-quality blocker that remains. Do not claim the data pipeline is healthy when it is only active but still returns stale K-line blockers.
