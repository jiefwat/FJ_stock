# Professional Stock Workbench V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the `d8747819` production baseline into a professional market and stock decision workstation while preserving authentication, holdings, routing, and deployment behavior.

**Architecture:** Keep local provider data and deterministic analysis as the primary decision source. Add a focused professional analytics module, fuse optional normalized research evidence only into coverage and evidence fields, and render the resulting provider-neutral protocol inside the existing native workspaces.

**Tech Stack:** Python 3.12, dataclasses, stdlib HTTP server, pytest, ruff, HTML/CSS/vanilla JavaScript.

---

## File Map

- Create `src/stock_ts/professional_analytics.py`: deterministic market pulse and stock evidence-matrix calculations.
- Create `src/stock_ts/research_fusion.py`: local-primary, provider-neutral evidence fusion.
- Create `tests/test_professional_analytics.py`: metric formulas, hard gates, evidence separation, and zero-data behavior.
- Create `tests/test_research_fusion.py`: local decision preservation, coverage enrichment, sanitization, and failure behavior.
- Modify `src/stock_ts/research_fallback.py`: expose market pulse and stock evidence sections from local data.
- Modify `src/stock_ts/web.py`: deliver local-primary analysis and optionally fuse external normalized evidence.
- Modify `src/stock_ts/webapp/engine_workspace.py`: render market pulse and stock evidence sections without a provider UI.
- Modify `src/stock_ts/webapp/styles.py`: use the desktop canvas and add responsive professional metric/evidence layouts.
- Modify `tests/test_research_fallback.py`: protect local market and stock professional contracts.
- Modify `tests/test_web_native_research_workspaces.py`: protect routes, visible language, and new semantic containers.
- Modify `tests/test_web_research_workspace_api.py`: protect local-primary API behavior and optional enrichment.
- Modify `docs/architecture/README.md`: document the deterministic-primary and enrichment-secondary boundary.
- Modify `docs/tech-specs/README.md`: document focused verification commands and provider-neutral output requirements.

### Task 1: Deterministic Professional Analytics

**Files:**
- Create: `src/stock_ts/professional_analytics.py`
- Create: `tests/test_professional_analytics.py`

- [ ] **Step 1: Write failing market-pulse tests**

Add tests that construct a `MarketSnapshot`, `SectorAnalysisReport`, and candidate universe, then assert:

```python
pulse = build_market_pulse(market, sectors, candidates)
assert pulse.advance_ratio == 0.60
assert pulse.breadth_ratio == 1.5
assert pulse.limit_balance == 26
assert pulse.extreme_up_count == 3
assert pulse.extreme_down_count == 1
assert pulse.confirmed_theme_count == 1
assert pulse.regime == "constructive"
assert pulse.risk_budget == "50%-70%"
```

Add a zero-data test asserting no division error, `coverage == 0`, `regime == "risk_off"`, and `risk_budget == "0%"`.

- [ ] **Step 2: Run the tests to verify RED**

Run:

```bash
python3 -m pytest tests/test_professional_analytics.py -q
```

Expected: collection fails because `stock_ts.professional_analytics` does not exist.

- [ ] **Step 3: Implement market pulse calculations**

Create frozen dataclasses `MarketPulseMetric` and `MarketPulse`. Implement:

```python
def build_market_pulse(
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    candidates: Sequence[CandidateStockRawData],
) -> MarketPulse:
    ...
```

Use explicit formulas from the design spec. Candidate extremes are labelled as scan-sample statistics. A theme is confirmed only when at least two candidate stocks in that theme rise at least 3%. Hard gates override constructive scores.

- [ ] **Step 4: Write failing stock evidence-matrix tests**

Assert that `build_stock_evidence_matrix(raw, report)` returns eight dimensions with separate support and counter-evidence, a confidence value, strengthen condition, and invalidation condition. Add a test where a high-scoring stock with a material negative event is blocked from an aggressive conclusion.

- [ ] **Step 5: Run stock matrix tests to verify RED**

Run the focused test and confirm failure because the stock matrix API is missing.

- [ ] **Step 6: Implement the stock evidence matrix**

Create frozen dataclasses `StockEvidenceDimension` and `StockEvidenceMatrix`. Convert the existing eight `StockAnalysisDimension` values into auditable records. Determine coverage from raw bars, fund flow, fundamentals, news, and announcements. Preserve `StockAnalysisDecision` as the action source and apply hard gates for stale/missing price evidence and material negative events.

- [ ] **Step 7: Verify GREEN and lint**

Run:

```bash
python3 -m pytest tests/test_professional_analytics.py -q
ruff check src/stock_ts/professional_analytics.py tests/test_professional_analytics.py
```

Expected: all tests pass and ruff reports no errors.

- [ ] **Step 8: Commit**

```bash
git add src/stock_ts/professional_analytics.py tests/test_professional_analytics.py
git commit -m "feat: add professional market and stock analytics"
```

### Task 2: Local Analysis as the Primary Workspace Result

**Files:**
- Modify: `src/stock_ts/research_fallback.py`
- Modify: `tests/test_research_fallback.py`

- [ ] **Step 1: Write failing local market contract tests**

Assert that local market research contains a first `market-pulse` section with metrics for participation, breadth, limit balance, scan extremes, theme participation, and evidence coverage. Assert the verdict and risk budget come from deterministic local inputs.

- [ ] **Step 2: Write failing local stock contract tests**

Assert that local stock research contains a `stock-evidence` section with eight items. Each item must expose score/confidence facts, supporting evidence in `summary`, counter-evidence in `risk`, and measurable strengthen/invalidation facts.

- [ ] **Step 3: Run focused tests to verify RED**

```bash
python3 -m pytest tests/test_research_fallback.py -q
```

Expected: failures for missing `market-pulse` and `stock-evidence` sections.

- [ ] **Step 4: Integrate professional analytics**

In `_build_market_research`, fetch the candidate universe once, build the market pulse, render pulse metrics as `ResearchModuleItem(kind="market_metric")`, and keep detailed breadth/themes below it.

In `_build_stock_research`, build the evidence matrix and render eight `ResearchModuleItem(kind="stock_evidence")` objects. Keep verdict, action, and risk sourced from the deterministic matrix decision.

- [ ] **Step 5: Verify GREEN and existing fallback behavior**

```bash
python3 -m pytest tests/test_professional_analytics.py tests/test_research_fallback.py -q
```

- [ ] **Step 6: Commit**

```bash
git add src/stock_ts/research_fallback.py tests/test_research_fallback.py
git commit -m "feat: make local professional analysis primary"
```

### Task 3: Optional Provider-Neutral Evidence Fusion

**Files:**
- Create: `src/stock_ts/research_fusion.py`
- Create: `tests/test_research_fusion.py`
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_research_workspace_api.py`

- [ ] **Step 1: Write failing fusion tests**

Construct local and enriched `ResearchWorkspaceResult` fixtures. Assert:

```python
fused = fuse_research_results(local, enriched)
assert fused.verdict == local.verdict
assert fused.action == local.action
assert fused.primary_risk == local.primary_risk
assert fused.delivery == "hybrid"
assert fused.coverage_ready > local.coverage_ready
```

Also assert enriched evidence can fill a missing stock dimension but cannot change the decision label, action, risk budget, target position, or invalidation rule. Assert public output contains none of `问财`, `iWencai`, `同花顺`, `skill`, `trace_id`, or `api_key`.

- [ ] **Step 2: Run fusion tests to verify RED**

Expected: import failure for `stock_ts.research_fusion`.

- [ ] **Step 3: Implement local-primary fusion**

Implement:

```python
def fuse_research_results(
    local: ResearchWorkspaceResult,
    enriched: ResearchWorkspaceResult,
) -> ResearchWorkspaceResult:
    ...
```

Match stock items by normalized label. Only replace local missing evidence or append bounded facts/details. Preserve local verdict, action, primary risk, decision label, conditions, and module ordering. Deduplicate findings and cap front findings at three.

- [ ] **Step 4: Write failing API delivery tests**

Patch the local builder and external service. Assert the API always builds local analysis, uses it unchanged when external research fails, and returns a fused result when external research succeeds. Existing authentication, request size, rate limit, and privacy tests must remain unchanged.

- [ ] **Step 5: Change `_research_workspace_response`**

Build the local result first. For a configured research service, obtain the bounded normalized external result and fuse it. Global snapshots store only fused provider-neutral payloads. When a fresh snapshot is used, retain its freshness label. On any external failure, return the local result with HTTP 200.

- [ ] **Step 6: Verify GREEN**

```bash
python3 -m pytest tests/test_research_fusion.py tests/test_web_research_workspace_api.py tests/test_research_snapshots.py -q
```

- [ ] **Step 7: Commit**

```bash
git add src/stock_ts/research_fusion.py src/stock_ts/web.py tests/test_research_fusion.py tests/test_web_research_workspace_api.py
git commit -m "feat: fuse optional research into local decisions"
```

### Task 4: Professional Market Pulse and Stock Evidence UI

**Files:**
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_native_research_workspaces.py`

- [ ] **Step 1: Write failing semantic UI tests**

Assert the native workspace script contains dedicated renderers for `market-pulse` and `stock-evidence`; the page contains no vendor-specific console, logo, provider name, skill list, or vendor endpoint; and the existing workspace/nav/hash attributes remain present.

- [ ] **Step 2: Run tests to verify RED**

```bash
python3 -m pytest tests/test_web_native_research_workspaces.py -q
```

Expected: failures for missing pulse/evidence renderers and classes.

- [ ] **Step 3: Implement market pulse rendering**

Add `renderEngineMarketPulseSection`. Render six compact metrics with value, label, and interpretation. Use text plus color for state. Keep source time and coverage in the header. Do not add a new button or route.

- [ ] **Step 4: Implement stock evidence rendering**

Add `renderEngineStockEvidenceSection`. Render each dimension with score, confidence, supporting evidence, counter-evidence, strengthen condition, and invalidation condition. Use existing safe DOM construction and `textContent`; never use raw HTML from API data.

- [ ] **Step 5: Implement responsive styles**

Increase the professional workspace maximum width from 1180 px to 1440 px, add a six-column pulse grid at wide desktop, three columns below 1180 px, and two/one columns on mobile. Add evidence cards with a quiet paper surface, visible focus, reduced motion, and no horizontal overflow.

- [ ] **Step 6: Verify UI tests and JavaScript contracts**

```bash
python3 -m pytest tests/test_web_native_research_workspaces.py tests/test_web_auth.py tests/test_auth.py -q
ruff check src tests
```

- [ ] **Step 7: Commit**

```bash
git add src/stock_ts/webapp/engine_workspace.py src/stock_ts/webapp/styles.py tests/test_web_native_research_workspaces.py
git commit -m "feat: add professional pulse and evidence surfaces"
```

### Task 5: Documentation and Regression Boundary

**Files:**
- Modify: `docs/architecture/README.md`
- Modify: `docs/tech-specs/README.md`
- Modify: `docs/superpowers/specs/2026-07-15-professional-stock-workbench-v2-design.md`

- [ ] **Step 1: Document the runtime boundary**

State that local provider analysis is primary, optional server-side enrichment can only add normalized evidence/coverage, public HTML/API are provider-neutral, and no new timer is introduced.

- [ ] **Step 2: Document verification commands**

Record focused analytics/fusion/UI tests, full `make lint`, the selected compatibility suite, browser viewport checks, and public deployment smoke checks.

- [ ] **Step 3: Run repository checks**

```bash
git diff --check
make lint
python3 -m pytest -q \
  tests/test_professional_analytics.py \
  tests/test_research_fusion.py \
  tests/test_research_fallback.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_native_research_workspaces.py \
  tests/test_research_snapshots.py \
  tests/test_auth.py \
  tests/test_web_auth.py \
  tests/test_systemd_timer_contract.py
```

Expected: all selected tests pass. Separately record that the legacy-vs-native test conflict existed at the `d8747819` baseline and is not introduced by this branch.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/README.md docs/tech-specs/README.md docs/superpowers/specs/2026-07-15-professional-stock-workbench-v2-design.md
git commit -m "docs: document professional research boundaries"
```

### Task 6: Local Browser Verification and Production Deployment

**Files:**
- No source changes expected.

- [ ] **Step 1: Start an isolated local server**

Run with temporary auth/user/report directories and a non-production port. Verify `/healthz`, login, authenticated market, stock, portfolio, opportunity, data-center, and account workspaces.

- [ ] **Step 2: Verify desktop and mobile**

Use browser checks at 1440 x 900, 1280 x 720, and 390 x 844. Verify no horizontal overflow, the pulse and evidence layouts are readable, hash navigation works, forms remain usable, and the console has no errors.

- [ ] **Step 3: Review the exact deployment diff**

Confirm the branch contains only intended source, tests, and docs; no `.env`, account database, holdings, snapshots, reports, credentials, or generated browser assets are tracked.

- [ ] **Step 4: Back up and deploy**

On `admin@47.82.145.207`, record the current commit, create a timestamped source backup under `/opt/stock-ts/.deploy_backups/`, deploy the tested branch while preserving runtime data, and restart only `stock-ts.service`.

- [ ] **Step 5: Run public verification**

Verify:

```text
GET /healthz = 200 and body ok
GET / = 303 to /login
GET /login = 200
authenticated market = 200 and professional pulse visible
authenticated stock = 200 and evidence matrix visible
stock-ts.service = active
existing daily-analysis, daily-research, and morning-email timers = active
new timer count = 0
```

- [ ] **Step 6: Roll back on any core regression**

If login, account, holdings, navigation, market, or stock verification fails, restore `d8747819`, restart `stock-ts.service`, and re-run the public smoke checks before reporting status.
