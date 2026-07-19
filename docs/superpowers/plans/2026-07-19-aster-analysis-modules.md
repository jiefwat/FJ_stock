# Aster Market Analysis Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic market analysis, opportunity discovery, stock analysis, and browser-private holdings to the deployed Aster Market desktop application.

**Architecture:** Extend the immutable snapshot model with supplier-neutral stock profiles, then derive all analysis in a new pure `analysis.py` module. The standard-library server exposes four read-only endpoints; server-rendered module decks use vanilla JavaScript for navigation and stock lookup, while holdings remain exclusively in browser localStorage.

**Tech Stack:** Python 3.11+ standard library, dataclasses, JSON, HTML/CSS/SVG, vanilla JavaScript, localStorage, pytest, Ruff.

---

### Task 1: Extend the snapshot with stock profiles

**Files:**
- Modify: `src/aster_market/models.py`
- Modify: `src/aster_market/snapshot.py`
- Modify: `tests/fixtures/market_snapshot.json`
- Create: `tests/test_stock_snapshot.py`

- [ ] **Step 1: Write failing stock-profile parser tests**

```python
def test_snapshot_merges_stock_profiles_by_code() -> None:
    result = load_snapshot(FIXTURE)
    assert result.snapshot is not None
    stock = result.snapshot.stocks[0]
    assert stock.code == "300100"
    assert stock.bars[-1].close == 32.45
    assert stock.valuation.pe_ttm == 28.4


def test_stock_profile_preserves_missing_optional_values() -> None:
    result = load_snapshot(FIXTURE)
    assert result.snapshot is not None
    stock = next(item for item in result.snapshot.stocks if item.code == "688981")
    assert stock.flow.inside_volume is None
    assert stock.valuation.pb is None
```

- [ ] **Step 2: Verify RED**

Run `PYTHONPATH=src python -m pytest -q tests/test_stock_snapshot.py`.
Expected: collection fails because `MarketSnapshot` has no `stocks` field.

- [ ] **Step 3: Implement immutable stock models**

Add frozen `PriceBar`, `ValuationSnapshot`, `FlowSnapshot`, and `StockProfile` dataclasses. `StockProfile` contains code, name, sector, bars, valuation, flow, data-quality fields, reliability, and stock-specific events. Add `stocks: tuple[StockProfile, ...]` to `MarketSnapshot`.

- [ ] **Step 4: Parse and merge stock sources**

Parse `stocks` first, then merge candidate fields by code. Keep only profiles with at least one valid close, sort by code, preserve absent numbers as `None`, and never expose source error strings. Add realistic valuation, flow, quality, and stock news fields to the fixture.

- [ ] **Step 5: Verify GREEN and commit**

Run `PYTHONPATH=src python -m pytest -q tests/test_models.py tests/test_snapshot.py tests/test_stock_snapshot.py` and `ruff check src tests`.
Commit with `[股票档案] 建立供应商中立股票快照`.

### Task 2: Build deterministic analysis engines

**Files:**
- Create: `src/aster_market/analysis.py`
- Create: `tests/test_analysis.py`
- Modify: `src/aster_market/presenter.py`
- Modify: `tests/test_presenter.py`

- [ ] **Step 1: Write failing market-analysis tests**

```python
def test_market_analysis_exposes_four_evidence_dimensions(snapshot) -> None:
    analysis = build_market_analysis(snapshot)
    assert analysis["regime"] == "轮动"
    assert [item["key"] for item in analysis["evidence"]] == [
        "index_direction", "participation", "limit_pressure", "concentration"
    ]
    assert analysis["next_check"]
```

- [ ] **Step 2: Write failing opportunity-stage tests**

```python
def test_opportunities_classify_spread_acceleration_and_divergence(snapshot) -> None:
    opportunities = build_opportunities(snapshot)
    assert opportunities[0]["stage"] == "扩散"
    assert opportunities[0]["invalidation"] == "上涨占比跌破 50% 或分歧升高"
    assert len(opportunities[0]["candidates"]) <= 5
```

- [ ] **Step 3: Write failing stock-analysis tests**

```python
def test_stock_analysis_derives_trend_momentum_and_volatility(stock) -> None:
    detail = analyze_stock(stock)
    assert detail["trend"]["label"] in {"强", "平", "弱", "样本不足"}
    assert detail["momentum"]["return_5d"] == 4.01
    assert detail["volatility"]["range_10d"] is not None


def test_stock_search_matches_code_name_and_sector(snapshot) -> None:
    assert search_stocks(snapshot, "300100")[0]["code"] == "300100"
    assert search_stocks(snapshot, "机器人")[0]["sector"] == "机器人"
    assert len(search_stocks(snapshot, "")) <= 20
```

- [ ] **Step 4: Verify RED and implement pure functions**

Run `PYTHONPATH=src python -m pytest -q tests/test_analysis.py`.
Implement `build_market_analysis`, `build_opportunities`, `analyze_stock`, `search_stocks`, and `find_stock`. All outputs are JSON-compatible, missing values stay `None`, and no function reads files or environment variables.

- [ ] **Step 5: Add summaries to the page presenter**

`build_view` adds `market_analysis` and the first eight `opportunities`; it does not embed full stock histories. Update presenter tests to assert both summaries and supplier-field isolation.

- [ ] **Step 6: Verify GREEN and commit**

Run `PYTHONPATH=src python -m pytest -q tests/test_analysis.py tests/test_presenter.py` and `ruff check src tests`.
Commit with `[分析引擎] 建立大盘机会与个股分析`.

### Task 3: Expose read-only analysis APIs

**Files:**
- Modify: `src/aster_market/web.py`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Write failing route tests**

```python
def test_analysis_routes_return_supplier_neutral_json() -> None:
    with running_server() as base_url:
        _, _, market = _get(f"{base_url}/api/analysis/market")
        _, _, opportunities = _get(f"{base_url}/api/opportunities")
        _, _, stocks = _get(f"{base_url}/api/stocks?query=机器人")
        _, _, detail = _get(f"{base_url}/api/stocks/300100")
    assert json.loads(market)["regime"] == "轮动"
    assert json.loads(opportunities)["items"]
    assert json.loads(stocks)["items"][0]["code"] == "300100"
    assert json.loads(detail)["code"] == "300100"
```

- [ ] **Step 2: Write failing error-contract tests**

Assert unknown stock returns 404 JSON, queries longer than 40 characters return 400, and missing snapshot returns 503 on all analysis endpoints. Assert every response has `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

- [ ] **Step 3: Verify RED and implement routes**

Parse query parameters with `urllib.parse.parse_qs`. Load the snapshot once per request, route business work to `analysis.py`, and return exactly the four documented endpoints. Do not add POST, PUT, PATCH, or DELETE handlers.

- [ ] **Step 4: Verify GREEN and commit**

Run `PYTHONPATH=src python -m pytest -q tests/test_web.py` and `ruff check src tests`.
Commit with `[分析接口] 开放四类只读分析查询`.

### Task 4: Build the four desktop module decks

**Files:**
- Create: `src/aster_market/ui_modules.py`
- Create: `src/aster_market/assets/modules.css`
- Modify: `src/aster_market/ui.py`
- Modify: `src/aster_market/web.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing module-structure tests**

```python
def test_ui_contains_four_analysis_decks(sample_view) -> None:
    html = render_app(sample_view)
    for module in ("market", "opportunities", "stock", "portfolio"):
        assert f'data-module-deck="{module}"' in html
    assert "大盘分析" in html
    assert "市场机会" in html
    assert "股票分析" in html
    assert "我的持仓" in html
```

Also assert no viewport meta, sidebar, mobile navigation, card grid, `@media (max-width`, old product marker, or unescaped external content.

- [ ] **Step 2: Verify RED**

Run `PYTHONPATH=src python -m pytest -q tests/test_ui.py`.
Expected: fails because the new deck markers do not exist.

- [ ] **Step 3: Render the market and opportunity decks**

Move focused section renderers into `ui_modules.py`. The market deck contains the horizon plus four evidence rows. The opportunity deck contains a continuous corridor with stage, evidence, up to five candidates, and invalidation text.

- [ ] **Step 4: Render stock and portfolio shells**

The stock deck contains a result rail, stock header, trend SVG region, six analysis dimensions, event list, loading/error/empty states, and stable `data-*` hooks. The portfolio deck contains a privacy statement, add/edit form, ledger columns, exposure strip, totals, and an empty state. Do not render example holdings.

- [ ] **Step 5: Apply the analysis-deck visual system**

Add `modules.css` using only existing Aster tokens. Use horizontal strips and ledger rules, not rounded cards. Preserve `min-width: 1180px`, keyboard focus, `prefers-reduced-motion`, and the single 420ms trajectory reveal.

- [ ] **Step 6: Verify GREEN and commit**

Run `PYTHONPATH=src python -m pytest -q tests/test_ui.py tests/test_web.py` and `ruff check src tests`.
Commit with `[界面模块] 构建四模块分析甲板`.

### Task 5: Implement module navigation, stock lookup, and local holdings

**Files:**
- Modify: `src/aster_market/assets/app.js`
- Create: `src/aster_market/assets/portfolio.js`
- Modify: `src/aster_market/ui.py`
- Modify: `src/aster_market/web.py`
- Modify: `tests/test_ui.py`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Write failing asset-contract tests**

Assert JavaScript contains the storage key `aster.portfolio.v1`, uses `localStorage`, fetches only GET stock endpoints, renders missing values as `—`, and never calls `fetch` with a body or non-GET method.

- [ ] **Step 2: Verify RED and implement module navigation**

Top navigation toggles one deck at a time, updates `location.hash`, restores the hash on load, and moves focus to the selected module heading. Existing refresh behavior remains.

- [ ] **Step 3: Implement stock search and detail rendering**

Debounce search by 180ms, cap input at 40 characters, fetch `/api/stocks?query=...`, then fetch the selected `/api/stocks/<code>`. Render trend, momentum, volatility, valuation, flow, events, quality, loading, no-result, and error states without `innerHTML` for external text.

- [ ] **Step 4: Implement browser-private holdings**

`portfolio.js` validates code, positive quantity, and non-negative cost; serializes only `{code, quantity, cost}` to `aster.portfolio.v1`; fetches public stock detail by code; calculates market value, total cost, P/L, return, sector exposure, and concentration locally. Add, edit, delete, corrupted-storage recovery, missing-stock, and empty states.

- [ ] **Step 5: Browser verification**

Use a real browser to verify module switching, stock search, one add/edit/delete holding cycle, persistence after reload, and no network request containing quantity or cost. Check 1280, 1536, and 1920 widths and console logs.

- [ ] **Step 6: Verify and commit**

Run full pytest, Ruff, compileall, credential scan, and the mobile-code scan. Commit with `[持仓模块] 实现浏览器私有持仓账本`.

### Task 6: Document, review, push, and deploy

**Files:**
- Modify: `docs/architecture/README.md`
- Modify: `docs/tech-specs/README.md`
- Modify: `docs/agent-ops/README.md`
- Modify: `docs/TODO.md`
- Modify: `docs/superpowers/README.md`
- Create: `docs/superpowers/aster-analysis-modules/README.md`
- Create: `docs/superpowers/aster-analysis-modules/TODO.md`
- Create: `docs/superpowers/aster-analysis-modules/review.md`
- Create: `docs/superpowers/aster-analysis-modules/test.md`

- [ ] **Step 1: Update product and operator documentation**

Document all four modules, deterministic formulas, API contracts, localStorage privacy, error states, runtime snapshot fields, deployment and rollback. State explicitly that holdings are not server data.

- [ ] **Step 2: Run code review and fix findings with TDD**

Review data truth, API exposure, HTML escaping, localStorage privacy, query limits, missing values, existing-route regression, and deployment isolation. Record findings and residual risks in `review.md`.

- [ ] **Step 3: Run final verification**

Run `pytest -q`, `ruff check src tests`, `compileall`, real-snapshot HTTP checks, 1280/1536/1920 browser checks, and scans for credentials, mobile code, write endpoints, request bodies containing holdings, old product markers, and internal URLs. Record exact evidence in `test.md`.

- [ ] **Step 4: Push and deploy**

Push `codex/aster-analysis-modules`, deploy an atomic release under `/opt/aster-market/releases`, preserve the current release for rollback, restart only the Aster main service, and verify the public homepage plus all four new APIs. Confirm Signal Desk and Nginx remain active.

- [ ] **Step 5: Complete release record**

Mark the active TODO complete, commit `[发布记录] 完成四模块公网验收`, push, deploy the final documentation commit, and repeat public health checks.
