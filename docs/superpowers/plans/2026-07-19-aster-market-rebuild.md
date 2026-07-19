# Aster Market Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publicly deploy a new read-only A-share market application with no inherited StockTs code or visual language.

**Architecture:** A small Python standard-library service reads one documented JSON snapshot, maps it into immutable domain models, derives supplier-neutral market signals, and serves a desktop HTML application plus a JSON API. CSS and JavaScript are standalone assets; missing data produces an explicit unavailable state rather than demo prices.

**Tech Stack:** Python 3.11+, stdlib `http.server`, dataclasses, JSON, HTML/CSS/SVG, vanilla JavaScript, pytest, Ruff.

---

### Task 1: Create the new project and domain contract

**Files:**
- Create: `AGENTS.md`
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/aster_market/__init__.py`
- Create: `src/aster_market/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing model test**

```python
from aster_market.models import IndexQuote, MarketSnapshot

def test_market_snapshot_is_immutable():
    snapshot = MarketSnapshot(
        trade_date="2026-07-18",
        generated_at="2026-07-18T15:10:00+08:00",
        source="market-snapshot",
        indices=(IndexQuote("上证指数", "000001.SH", 3501.26, 0.48),),
        advancing=2841,
        declining=2134,
        limit_up=61,
        limit_down=8,
        northbound_net_inflow=12.4,
        sectors=(),
        candidates=(),
        news=(),
    )
    assert snapshot.indices[0].pct_change == 0.48
```

- [ ] **Step 2: Verify RED**

Run `PYTHONPATH=src python -m pytest -q tests/test_models.py`.
Expected: import failure because `aster_market.models` does not exist.

- [ ] **Step 3: Implement immutable models**

Create frozen dataclasses `IndexQuote`, `SectorPulse`, `Candidate`, `NewsItem`, and `MarketSnapshot`. Use tuples for collections and only supplier-neutral field names from the design spec.

- [ ] **Step 4: Add the standard project command surface**

`pyproject.toml` declares package `aster-market`, Python `>=3.11`, Ruff line length 100 and pytest `testpaths=["tests"]`. `Makefile` exposes `install`, `lint`, `test`, and `run`; `run` executes `PYTHONPATH=src python -m aster_market.web`.

- [ ] **Step 5: Verify GREEN and commit**

Run the model test and commit with `[项目初始化] 建立 Aster Market 领域骨架`.

### Task 2: Parse snapshots and derive market state

**Files:**
- Create: `src/aster_market/snapshot.py`
- Create: `src/aster_market/presenter.py`
- Create: `tests/fixtures/market_snapshot.json`
- Create: `tests/test_snapshot.py`
- Create: `tests/test_presenter.py`

- [ ] **Step 1: Write failing parser tests**

```python
from pathlib import Path
from aster_market.snapshot import load_snapshot

def test_load_snapshot_maps_market_and_candidates():
    result = load_snapshot(Path("tests/fixtures/market_snapshot.json"))
    assert result.status == "ready"
    assert result.snapshot.trade_date == "2026-07-18"
    assert result.snapshot.candidates[0].code == "300100"

def test_missing_snapshot_is_explicitly_unavailable(tmp_path):
    result = load_snapshot(tmp_path / "missing.json")
    assert result.status == "unavailable"
    assert result.snapshot is None
```

- [ ] **Step 2: Verify RED**

Run `PYTHONPATH=src python -m pytest -q tests/test_snapshot.py tests/test_presenter.py`.

- [ ] **Step 3: Implement the adapter**

`load_snapshot(path)` returns `SnapshotResult(status, message, snapshot)`. It accepts the documented `market`, `sectors`, `candidate_universe.items`, `stocks`, and `market_news` fields; malformed values become empty collections or an unavailable result.

- [ ] **Step 4: Implement state derivation**

`build_view(snapshot)` returns a dictionary with `regime`, `risk_level`, `breadth_ratio`, ordered sectors, ordered candidates, horizon SVG points, and no supplier-specific fields. Regime rules are deterministic: breadth >= 0.58 and limit-down <= 10 is `扩张`; breadth <= 0.42 or limit-down >= 25 is `收缩`; otherwise `轮动`.

- [ ] **Step 5: Verify GREEN and commit**

Run parser and presenter tests and commit with `[市场数据] 建立只读快照与态势推导`.

### Task 3: Build the completely new desktop interface

**Files:**
- Create: `src/aster_market/ui.py`
- Create: `src/aster_market/assets/app.css`
- Create: `src/aster_market/assets/app.js`
- Create: `tests/test_ui.py`

- [ ] **Step 1: Write the failing UI contract test**

```python
from aster_market.ui import render_app

def test_ui_uses_market_horizon_and_no_stockts_patterns(sample_view):
    html = render_app(sample_view)
    assert 'data-aster-app="market-horizon"' in html
    assert 'data-market-horizon' in html
    assert "StockTS" not in html
    assert "desktop-sidebar" not in html
    assert 'name="viewport"' not in html
    assert "@media (max-width" not in html
```

- [ ] **Step 2: Verify RED**

Run `PYTHONPATH=src python -m pytest -q tests/test_ui.py`.

- [ ] **Step 3: Implement HTML and asset routes**

Render a horizontal command band, market conclusion, SVG horizon, theme field, action timeline, candidate stream and news stream. Escape every external string with `html.escape`; use JSON only through `json.dumps`.

- [ ] **Step 4: Apply the Aster visual system**

CSS uses ceramic white, cobalt blue, signal orange, seaweed green and ink. No left sidebar, dark terminal shell, serif headline, numbered workspace navigation, yellow-brass rail, rounded dashboard card grid, phone media query or inherited class name.

- [ ] **Step 5: Implement restrained interaction**

JavaScript supports horizontal view filters, stock search within the rendered candidate stream, refresh via `location.reload()`, and one 420ms horizon reveal animation disabled by `prefers-reduced-motion`.

- [ ] **Step 6: Verify GREEN and commit**

Run UI tests, Ruff and a local browser screenshot at 1280, 1536 and 1920 widths. Commit with `[界面设计] 构建市场地形工作台`.

### Task 4: Serve, document, test, and deploy

**Files:**
- Create: `src/aster_market/web.py`
- Create: `tests/test_web.py`
- Create: `docs/agent-ops/README.md`
- Create: `docs/architecture/README.md`
- Create: `docs/tech-specs/README.md`
- Create: `docs/TODO.md`
- Create: `docs/superpowers/README.md`
- Create: `docs/superpowers/历史需求索引.md`
- Create: `docs/superpowers/aster-market-rebuild/README.md`
- Create: `docs/superpowers/aster-market-rebuild/TODO.md`

- [ ] **Step 1: Write failing HTTP tests**

Start `ThreadingHTTPServer` on port 0 and assert `/healthz` returns `ok`, `/api/snapshot` returns JSON, `/` returns the Aster marker, and all dynamic responses include `Cache-Control: no-store` plus `X-Content-Type-Options: nosniff`.

- [ ] **Step 2: Verify RED and implement the server**

Routes are exactly `/`, `/healthz`, `/api/snapshot`, `/assets/app.css`, and `/assets/app.js`; other paths return JSON or text 404. Bind from `HOST` and `PORT`; read `ASTER_SNAPSHOT_PATH` on each request so refreshed files appear without restart.

- [ ] **Step 3: Build governance and operator docs**

Document startup, architecture, JSON contract, public read-only boundary, deployment process and the active superpower requirement. Do not copy old StockTs docs.

- [ ] **Step 4: Run final verification**

Run `python -m py_compile`, `ruff check`, `pytest -q`, local `/healthz`, `/api/snapshot`, three desktop browser checks, and scan for `StockTS`, `desktop-sidebar`, mobile code, credentials and internal URLs.

- [ ] **Step 5: Push the orphan branch**

Push `codex/aster-market-rebuild` to GitHub. Do not merge old branches into it.

- [ ] **Step 6: Replace public deployment**

Deploy to `/opt/aster-market`, copy the server runtime snapshot to `/opt/aster-market/data/market_snapshot.json`, update `stock-ts.service` to run `python -m aster_market.web`, remove authentication drop-in dependencies from the active service, restart only that service, and verify public `/`, `/healthz`, and `/api/snapshot`. Signal Desk and Nginx remain untouched.
