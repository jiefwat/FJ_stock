# Market Intelligence Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and locally run a verified A-share decision workbench covering Today, Market, Opportunities, Stock Lab, Watchlist, and Data Center.

**Architecture:** A FastAPI backend owns provider access, normalization, deterministic scoring, caching, and local persistence. A React/Vite frontend consumes only versioned local APIs and presents an editorial market-desk workflow. Eastmoney and FRED provide no-key core data; semantic research is an optional enrichment provider represented explicitly in provider health.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, HTTPX, SQLite, pytest, Ruff, mypy, React 19, TypeScript, Vite, TanStack Query, ECharts, Vitest, Testing Library, Playwright.

---

## File Map

- `backend/pyproject.toml`: backend dependencies and quality-tool configuration.
- `backend/src/marketdesk/config.py`: environment and cache settings.
- `backend/src/marketdesk/models.py`: normalized API and analysis contracts.
- `backend/src/marketdesk/providers/base.py`: provider protocol and provider errors.
- `backend/src/marketdesk/providers/eastmoney.py`: A-share, sector, quote, and K-line retrieval.
- `backend/src/marketdesk/providers/fred.py`: macro retrieval.
- `backend/src/marketdesk/store.py`: SQLite snapshots, watchlist, and provider-health persistence.
- `backend/src/marketdesk/analysis/market.py`: market regime calculation.
- `backend/src/marketdesk/analysis/opportunities.py`: hard gates and candidate scoring.
- `backend/src/marketdesk/analysis/stock.py`: technical indicators and stock stance.
- `backend/src/marketdesk/services.py`: application orchestration and stale-cache fallback.
- `backend/src/marketdesk/api.py`: FastAPI routes and static-app serving.
- `frontend/src/app/*`: shell, routing, global query/error handling, and styles.
- `frontend/src/features/*`: one directory for each user-visible module.
- `frontend/src/lib/api.ts`: typed local API client.
- `scripts/setup.sh`, `scripts/dev.sh`, `scripts/start.sh`, `scripts/verify.sh`: operator commands.
- `tests/browser/smoke.spec.ts`: browser workflow and desktop layout checks.
- `README.md`: setup, operation, data-source boundaries, and troubleshooting.

### Task 1: Repository and Contract Foundation

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/marketdesk/__init__.py`
- Create: `backend/src/marketdesk/config.py`
- Create: `backend/src/marketdesk/models.py`
- Create: `backend/tests/test_models.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `Makefile`

- [ ] **Step 1: Write failing model tests**

```python
from datetime import datetime, timezone

from marketdesk.models import DatasetMeta, Freshness


def test_dataset_meta_rejects_invalid_coverage() -> None:
    now = datetime.now(timezone.utc)
    try:
        DatasetMeta(source="eastmoney", observed_at=now, fetched_at=now, freshness=Freshness.FRESH, coverage=1.2)
    except ValueError:
        return
    raise AssertionError("coverage above one must fail")
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `cd backend && uv run pytest tests/test_models.py -q`

Expected: collection fails because `marketdesk.models` does not exist.

- [ ] **Step 3: Add the backend package and normalized contracts**

Define `Freshness`, `DatasetMeta`, `IndexQuote`, `EquityQuote`, `SectorSnapshot`, `MarketSnapshot`, `OpportunityCandidate`, `StockDossier`, `ProviderHealth`, and `WatchlistItem` as strict Pydantic models. `DatasetMeta.coverage` must use `Field(ge=0, le=1)`, timestamps must be timezone-aware, and numeric fields that can be absent must be `float | None` rather than magic zeroes.

- [ ] **Step 4: Add pinned project configuration and Make targets**

`backend/pyproject.toml` must expose the `marketdesk` package and development dependencies. `frontend/package.json` must define `dev`, `build`, `test`, `typecheck`, and `lint` scripts. The root Makefile delegates to `scripts/*.sh` and does not embed process-control logic.

- [ ] **Step 5: Run model tests and commit**

Run: `cd backend && uv run pytest tests/test_models.py -q`

Expected: all model tests pass.

Commit: `git commit -am "build: establish workbench contracts"` after adding the new files.

### Task 2: Provider Adapters, Cache, and Health

**Files:**
- Create: `backend/src/marketdesk/providers/__init__.py`
- Create: `backend/src/marketdesk/providers/base.py`
- Create: `backend/src/marketdesk/providers/eastmoney.py`
- Create: `backend/src/marketdesk/providers/fred.py`
- Create: `backend/src/marketdesk/store.py`
- Create: `backend/tests/fixtures/eastmoney_market.json`
- Create: `backend/tests/fixtures/eastmoney_sectors.json`
- Create: `backend/tests/fixtures/eastmoney_kline.json`
- Create: `backend/tests/test_eastmoney_provider.py`
- Create: `backend/tests/test_store.py`

- [ ] **Step 1: Capture bounded provider fixtures and write failing normalization tests**

```python
def test_market_payload_normalizes_percent_units(provider, market_payload):
    snapshot = provider.normalize_market(market_payload)
    assert snapshot.indices[0].symbol == "SH.000001"
    assert snapshot.indices[0].change_pct == -3.05
    assert snapshot.meta.coverage == 1.0
```

Fixtures contain only the fields used by the application and no cookies or credentials.

- [ ] **Step 2: Verify provider tests fail**

Run: `cd backend && uv run pytest tests/test_eastmoney_provider.py tests/test_store.py -q`

Expected: failures for missing providers and store.

- [ ] **Step 3: Implement providers and normalization**

Use one shared `httpx.AsyncClient` with a 10-second timeout, two retries for idempotent reads, bounded page sizes, and a descriptive user agent. Convert Eastmoney scaled integer fields to displayed values, map security IDs to `market.code`, and raise `ProviderUnavailable` for malformed or empty payloads.

FRED reads CSV series by identifier, skips missing observations, and returns the latest valid dated value. Do not use Yahoo because the live probe is unreliable in the target environment.

- [ ] **Step 4: Implement SQLite snapshots and provider health**

Create tables for `snapshots`, `provider_health`, `watchlist`, and `refresh_runs`. Snapshot writes are idempotent on `(dataset, observed_at, payload_hash)`. Reads return the newest snapshot plus computed cache age. SQLite initialization must be safe on repeated startup.

- [ ] **Step 5: Test live-provider contracts without making tests depend on the network**

Unit tests use fixtures and HTTPX mock transports. Add a separate `scripts/check_live_data.py` command for live verification; it is not part of the hermetic unit suite.

- [ ] **Step 6: Run tests and commit**

Run: `cd backend && uv run pytest tests/test_eastmoney_provider.py tests/test_store.py -q`

Expected: all provider and store tests pass.

Commit: `git commit -am "feat: add resilient market data providers"` after staging new files.

### Task 3: Market Analysis Service and APIs

**Files:**
- Create: `backend/src/marketdesk/analysis/__init__.py`
- Create: `backend/src/marketdesk/analysis/market.py`
- Create: `backend/src/marketdesk/services.py`
- Create: `backend/src/marketdesk/api.py`
- Create: `backend/tests/test_market_analysis.py`
- Create: `backend/tests/test_market_api.py`

- [ ] **Step 1: Write failing market-regime tests**

```python
def test_missing_factor_renormalizes_weights(snapshot):
    snapshot.external_risk = None
    result = analyse_market(snapshot)
    assert sum(f.weight for f in result.factors if f.available) == 1.0
    assert result.confidence < 1.0
```

Cover threshold boundaries, missing factors, advancing/declining counts, and zero-as-missing handling.

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/test_market_analysis.py tests/test_market_api.py -q`

- [ ] **Step 3: Implement deterministic market analysis**

Implement factor normalization and the weights from the design specification. Return the market score, regime, confidence, factor evidence, breadth, turnover, indices, and sectors. Missing factors lower confidence and renormalize available weights.

- [ ] **Step 4: Implement stale-cache orchestration and routes**

Expose `GET /api/v1/today`, `GET /api/v1/market`, `GET /api/v1/data-status`, `POST /api/v1/refresh`, and `GET /healthz`. Live fetch success writes a snapshot; fetch failure serves a cache marked stale; total absence returns a structured partial response.

- [ ] **Step 5: Run tests and commit**

Run: `cd backend && uv run pytest tests/test_market_analysis.py tests/test_market_api.py -q`

Expected: all tests pass, including simulated provider failure.

Commit: `git commit -am "feat: expose market decision APIs"` after staging new files.

### Task 4: Opportunity Funnel

**Files:**
- Create: `backend/src/marketdesk/analysis/opportunities.py`
- Create: `backend/tests/test_opportunities.py`
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`

- [ ] **Step 1: Write failing gate and scoring tests**

```python
def test_st_security_is_excluded(candidate):
    candidate.name = "*ST Example"
    result = rank_candidates([candidate], market_regime="balanced")
    assert result.excluded[0].reasons == ["special_treatment"]


def test_score_components_sum_to_total(candidate):
    ranked = rank_candidates([candidate], market_regime="balanced").candidates[0]
    assert round(sum(item.weighted_score for item in ranked.components), 2) == ranked.score
```

- [ ] **Step 2: Verify failure**

Run: `cd backend && uv run pytest tests/test_opportunities.py -q`

- [ ] **Step 3: Implement presets, hard gates, scoring, and CSV output**

Implement `trend`, `sector_improving`, `capital_confirmed`, and `oversold_rebound` presets. Exclude ST, delisting-risk, invalid price, suspended, insufficient amount, and insufficient market cap. Return funnel counts, excluded-reason counts, score components, risk flags, and evidence completeness.

- [ ] **Step 4: Add routes**

Expose `GET /api/v1/opportunities?preset=trend&limit=50` and `GET /api/v1/opportunities/export.csv` with the same filters. Reject unknown presets with HTTP 422.

- [ ] **Step 5: Run tests and commit**

Run: `cd backend && uv run pytest tests/test_opportunities.py tests/test_market_api.py -q`

Commit: `git commit -am "feat: add auditable opportunity funnel"` after staging new files.

### Task 5: Stock Lab and Search

**Files:**
- Create: `backend/src/marketdesk/analysis/stock.py`
- Create: `backend/tests/test_stock_analysis.py`
- Create: `backend/tests/test_stock_api.py`
- Modify: `backend/src/marketdesk/providers/eastmoney.py`
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`

- [ ] **Step 1: Write failing indicator and insufficient-data tests**

```python
def test_stock_stance_is_insufficient_without_history(quote):
    result = analyse_stock(quote=quote, bars=[])
    assert result.stance == "insufficient_data"


def test_moving_averages_use_only_prior_and_current_bars(bars):
    result = calculate_indicators(bars)
    assert result.ma5 == sum(bar.close for bar in bars[-5:]) / 5
```

- [ ] **Step 2: Verify failure**

Run: `cd backend && uv run pytest tests/test_stock_analysis.py tests/test_stock_api.py -q`

- [ ] **Step 3: Implement search, quote, K-line, and technical analysis**

Search the cached A-share universe by code or Chinese name. Compute MA5/20/60, RSI14, MACD, 20-day volatility, volume ratio, support, and resistance. Build structured bull, bear, invalidation, and missing-evidence statements from facts only.

- [ ] **Step 4: Add Stock Lab routes**

Expose `GET /api/v1/search?q=`, `GET /api/v1/stocks/{symbol}`, and `GET /api/v1/stocks/{symbol}/chart`. Invalid symbols return 404; provider failure uses the most recent valid cached dossier where possible.

- [ ] **Step 5: Run tests and commit**

Run: `cd backend && uv run pytest tests/test_stock_analysis.py tests/test_stock_api.py -q`

Commit: `git commit -am "feat: add evidence-based stock lab"` after staging new files.

### Task 6: Watchlist Persistence

**Files:**
- Create: `backend/tests/test_watchlist_api.py`
- Modify: `backend/src/marketdesk/store.py`
- Modify: `backend/src/marketdesk/api.py`

- [ ] **Step 1: Write failing CRUD and validation tests**

Test create, list, update, delete, duplicate symbol, invalid status, empty thesis, and persistence across application instances.

- [ ] **Step 2: Verify failure**

Run: `cd backend && uv run pytest tests/test_watchlist_api.py -q`

- [ ] **Step 3: Implement watchlist APIs**

Expose `GET/POST /api/v1/watchlist`, `PATCH /api/v1/watchlist/{id}`, and `DELETE /api/v1/watchlist/{id}`. Allowed statuses are `new`, `researching`, `waiting`, `invalidated`, and `archived`. Store UTC timestamps and never delete snapshots when removing a watchlist row.

- [ ] **Step 4: Run tests and commit**

Run: `cd backend && uv run pytest tests/test_watchlist_api.py -q`

Commit: `git commit -am "feat: add local research watchlist"` after staging new files.

### Task 7: Frontend Shell and Today/Market Pages

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/styles.css`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/AsyncState.tsx`
- Create: `frontend/src/components/DataStamp.tsx`
- Create: `frontend/src/features/today/TodayPage.tsx`
- Create: `frontend/src/features/market/MarketPage.tsx`
- Create: `frontend/src/features/market/MarketChart.tsx`
- Create: `frontend/src/features/today/TodayPage.test.tsx`

- [ ] **Step 1: Write a failing Today page test**

```tsx
it("shows the regime, next actions, and data timestamp", async () => {
  render(<TodayPage />);
  expect(await screen.findByText("市场状态")).toBeInTheDocument();
  expect(screen.getByText("今天先做什么")).toBeInTheDocument();
  expect(screen.getByText(/数据时间/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Verify frontend test failure**

Run: `cd frontend && pnpm test --run src/features/today/TodayPage.test.tsx`

- [ ] **Step 3: Implement the editorial shell and typed query layer**

Use deep green navigation, warm paper surfaces, tabular numeric typography, red/amber/green icons plus text labels, and CSS variables. The shell includes desktop navigation, search, freshness status, refresh feedback, skip link, and route-level error handling.

- [ ] **Step 4: Implement Today and Market**

Render conclusions first and evidence second. Market includes index cards, breadth, factor waterfall, turnover, sector heat table, and source drawer. All charts have a text summary and do not rely on color alone.

- [ ] **Step 5: Test and commit**

Run: `cd frontend && pnpm test --run && pnpm typecheck && pnpm build`

Commit: `git commit -am "feat: build market desk shell and overview"` after staging new files.

### Task 8: Opportunities, Stock Lab, Watchlist, and Data Center UI

**Files:**
- Create: `frontend/src/features/opportunities/OpportunitiesPage.tsx`
- Create: `frontend/src/features/opportunities/OpportunityDrawer.tsx`
- Create: `frontend/src/features/stocks/StockLabPage.tsx`
- Create: `frontend/src/features/stocks/StockChart.tsx`
- Create: `frontend/src/features/watchlist/WatchlistPage.tsx`
- Create: `frontend/src/features/data/DataCenterPage.tsx`
- Create: `frontend/src/features/opportunities/OpportunitiesPage.test.tsx`
- Create: `frontend/src/features/stocks/StockLabPage.test.tsx`
- Modify: `frontend/src/app/router.tsx`

- [ ] **Step 1: Write failing workflow tests**

Test that an active preset is visible, score decomposition opens, search works by code, insufficient data is explicit, watchlist mutation updates the page, and Data Center displays provider health without credentials.

- [ ] **Step 2: Verify failures**

Run: `cd frontend && pnpm test --run src/features/opportunities/OpportunitiesPage.test.tsx src/features/stocks/StockLabPage.test.tsx`

- [ ] **Step 3: Implement all remaining pages**

Opportunity tables remain desktop-ranked lists. Stock Lab keeps the conclusion and missing evidence above the fold, with chart and evidence sections below. Watchlist uses status chips plus editable thesis/invalidation fields. Data Center shows coverage, timestamps, provider latency, error reason, retry, and optional semantic-research configuration status.

- [ ] **Step 4: Run frontend gates and commit**

Run: `cd frontend && pnpm test --run && pnpm typecheck && pnpm build`

Commit: `git commit -am "feat: complete research workflows"` after staging new files.

### Task 9: Local Operations and End-to-end Verification

**Files:**
- Create: `scripts/setup.sh`
- Create: `scripts/dev.sh`
- Create: `scripts/start.sh`
- Create: `scripts/verify.sh`
- Create: `scripts/check_live_data.py`
- Create: `tests/browser/package.json`
- Create: `tests/browser/playwright.config.ts`
- Create: `tests/browser/smoke.spec.ts`
- Create: `README.md`
- Modify: `backend/src/marketdesk/api.py`
- Modify: `Makefile`

- [ ] **Step 1: Write live-data and browser acceptance checks**

The live-data check asserts the required index set, at least 90% required-field coverage for the returned A-share universe, timezone-aware timestamps, no non-finite decision values, and graceful semantic-research-not-configured status.

The browser suite verifies Today -> Opportunities -> Stock Lab -> Watchlist, Data Center visibility, keyboard access to primary navigation, 1440 x 900 desktop without horizontal document overflow.

- [ ] **Step 2: Implement one-command setup and startup**

`make setup` installs locked dependencies. `make start` builds the frontend and starts one production-style FastAPI process that serves the SPA and APIs on `127.0.0.1:8765`. The script writes PID and logs under `.run/`, verifies `/healthz`, and reports the local URL. A second start must detect or safely replace only the project's own process.

- [ ] **Step 3: Implement the verification pipeline**

`make verify` runs Ruff, mypy, backend tests, frontend lint/typecheck/tests/build, live-data checks, then browser smoke tests. It exits on the first failing gate and prints the failing command.

- [ ] **Step 4: Document operation and limitations**

README includes exact setup/start/stop/test commands, module walkthrough, source/freshness rules, optional `IWENCAI_API_KEY`, licensing caution for public deployment, and troubleshooting for provider failure or stale cache.

- [ ] **Step 5: Run full verification, repair failures, and commit**

Run: `make setup && make verify && make start`

Then verify: `curl -fsS http://127.0.0.1:8765/healthz` and open the local app in the browser for the desktop workflow.

Expected: every gate passes; live data either meets coverage requirements or returns a visible structured partial state. Any failed gate requires repair and rerun before completion.

Commit: `git commit -am "chore: verify local market workbench"` after staging new files.

### Task 10: Final Audit

**Files:**
- Modify only files required by audit findings.

- [ ] **Step 1: Compare implementation to every design acceptance item**

Create a temporary checklist from sections 3 through 12 of the design and map each item to a route, test, or documented limitation. Do not commit the temporary checklist.

- [ ] **Step 2: Inspect data correctness in the running application**

Compare at least three index values and three stock quotes to their raw provider payloads. Confirm percentage scaling, market code mapping, observation timestamps, cache age, and stale labeling.

- [ ] **Step 3: Repeat functional and interaction workflows**

Exercise refresh, each opportunity preset, candidate evidence, stock search by code and name, add/edit/delete watchlist, CSV export, provider failure fallback.

- [ ] **Step 4: Rerun all gates after any repair**

Run: `make verify`

Expected: zero failures. Record any unavoidable external-source limitations plainly in README and Data Center rather than hiding them.

- [ ] **Step 5: Confirm clean repository and running local URL**

Run: `git status --short`, `curl -fsS http://127.0.0.1:8765/healthz`, and `git log --oneline -5`.

Expected: no uncommitted implementation changes, healthy local server, and auditable commits.
