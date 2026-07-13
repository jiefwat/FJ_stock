# Research Data Depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve market, financial, and valuation history in the existing snapshot and use minimum-sample cross-period evidence in market and stock research.

**Architecture:** Extend existing frozen domain models with default-empty history fields and teach only the TDX snapshot provider to parse the optional arrays. The refresh/enrichment scripts accumulate bounded, deduplicated history, while the research modules derive evidence from typed history without changing Phase 1 safety ordering or requiring a storage migration.

**Tech Stack:** Python 3.11+ dataclasses, JSON snapshots, existing TDX/Tushare/AKShare adapters, pytest, ruff, standard-library Web renderer.

---

## File Map

- Modify `src/stock_ts/models.py`: add typed market, financial, and valuation history points plus optional history fields.
- Modify `src/stock_ts/providers/tdx_snapshot_provider.py`: parse optional history arrays defensively.
- Modify `src/stock_ts/analysis.py`: propagate market history into `MarketSnapshot`.
- Modify `scripts/refresh_tdx_snapshot.py`: accumulate 60 deduplicated daily market observations.
- Modify `scripts/enrich_tdx_snapshot.py`: retain eight financial periods and 250 valuation points.
- Modify `src/stock_ts/research/market_regime.py`: derive breadth, liquidity, and risk direction from recent market history.
- Modify `src/stock_ts/research/stock_memo.py`: derive multi-period operating-quality evidence and internal PE percentile.
- Modify `tests/test_data_sources_tdx_snapshot.py`: verify typed history parsing and malformed-row isolation.
- Modify `tests/test_tdx_snapshot_refresh_script.py`: verify market-history accumulation, deduplication, and retention.
- Modify `tests/test_external_snapshot_enrichment.py`: verify financial and valuation history merging.
- Modify `tests/test_market_regime.py`: verify minimum-sample market evidence and risk priority.
- Modify `tests/test_stock_research_memo.py`: verify financial trends, valuation sample thresholds, and stale override.
- Modify `tests/test_web_market_research_workspace.py`: verify cross-period market evidence is visible.
- Modify `tests/test_web_stock_research_workspace.py`: verify financial-period and valuation-observation evidence is visible.
- Create `docs/research/research-data-depth-test-report.md`: record local, full-suite, preview, deployment, and rollback evidence.

## Task 1: Add typed history contracts and provider parsing

**Files:**
- Modify: `src/stock_ts/models.py`
- Modify: `src/stock_ts/providers/tdx_snapshot_provider.py`
- Modify: `src/stock_ts/analysis.py`
- Modify: `tests/test_data_sources_tdx_snapshot.py`

- [ ] **Step 1: Write failing provider tests**

Add this complete fixture helper and test:

```python
def _write_history_snapshot(tmp_path: Path) -> Path:
    snapshot = tmp_path / "history.json"
    bar = {"date": "2026-07-10", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000}
    snapshot.write_text(
        json.dumps(
            {
                "market": {
                    "trade_date": "2026-07-10",
                    "indices": [],
                    "advancing": 2500,
                    "declining": 2200,
                    "limit_up": 65,
                    "limit_down": 12,
                },
                "market_history": [
                    {"trade_date": "2026-07-10", "advancing": 2500, "declining": 2200, "breadth_ratio": 1.1364, "limit_up": 65, "limit_down": 12, "amount": 10200.0},
                    {"trade_date": "bad-date"},
                ],
                "stocks": {
                    "600519": {
                        "name": "贵州茅台",
                        "bars": [bar],
                        "fundamental_history": [
                            {"date": "2026-03-31", "source": "tushare.fina_indicator", "revenue_yoy": 12.0, "net_profit_yoy": 18.0},
                            {"date": "bad-date"},
                        ],
                        "valuation_history": [
                            {"date": "2026-07-10", "source": "tushare.daily_basic", "pe_ttm": 18.0, "pb": 2.1},
                            {"date": "bad-date"},
                        ],
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return snapshot


def test_tdx_snapshot_parses_typed_research_history(tmp_path: Path) -> None:
    snapshot = _write_history_snapshot(tmp_path)
    provider = TdxSnapshotProvider(snapshot)

    market = provider.fetch_market()
    stock = provider.fetch_stock("600519")

    assert [item.trade_date for item in market.history] == ["2026-07-10"]
    assert market.history[0].amount == 10200.0
    assert [item.date for item in stock.fundamental_history] == ["2026-03-31"]
    assert stock.fundamental_history[0].revenue_yoy == 12.0
    assert [item.date for item in stock.valuation_history] == ["2026-07-10"]
```

Also add an old-snapshot test that asserts all three history fields default to empty lists.

- [ ] **Step 2: Run the tests and confirm the history attributes are absent**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_data_sources_tdx_snapshot.py
```

Expected: FAIL because the typed history models and fields do not exist.

- [ ] **Step 3: Add immutable history models and default-empty fields**

Add to `models.py`:

```python
@dataclass(frozen=True)
class MarketHistoryPoint:
    trade_date: str
    advancing: int
    declining: int
    breadth_ratio: float
    limit_up: int
    limit_down: int
    amount: float


@dataclass(frozen=True)
class FundamentalPeriod:
    date: str
    source: str
    revenue_yoy: float | None = None
    net_profit_yoy: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    debt_to_assets: float | None = None
    ocf_to_profit: float | None = None


@dataclass(frozen=True)
class ValuationPoint:
    date: str
    source: str
    pe_ttm: float | None = None
    pb: float | None = None
    ps: float | None = None
```

Append default fields to existing dataclasses:

```python
MarketRawData.history: list[MarketHistoryPoint] = field(default_factory=list)
MarketSnapshot.history: list[MarketHistoryPoint] = field(default_factory=list)
StockRawData.fundamental_history: list[FundamentalPeriod] = field(default_factory=list)
StockRawData.valuation_history: list[ValuationPoint] = field(default_factory=list)
```

- [ ] **Step 4: Parse valid rows and ignore malformed rows**

Import the new models in `tdx_snapshot_provider.py`. Add an ISO-date validator and three parsers:

```python
def _valid_iso_date(value: object) -> str:
    text = str(value or "").strip()[:10]
    try:
        date.fromisoformat(text)
    except ValueError:
        return ""
    return text


def _market_history_from_payload(value: object) -> list[MarketHistoryPoint]:
    points: list[MarketHistoryPoint] = []
    for row in _as_list(value):
        if not isinstance(row, dict):
            continue
        trade_date = _valid_iso_date(row.get("trade_date"))
        if not trade_date:
            continue
        try:
            points.append(
                MarketHistoryPoint(
                    trade_date=trade_date,
                    advancing=int(row.get("advancing", 0)),
                    declining=int(row.get("declining", 0)),
                    breadth_ratio=float(row.get("breadth_ratio", 0.0)),
                    limit_up=int(row.get("limit_up", 0)),
                    limit_down=int(row.get("limit_down", 0)),
                    amount=float(row.get("amount", 0.0)),
                )
            )
        except (TypeError, ValueError):
            continue
    return sorted(points, key=lambda item: item.trade_date)
```

Implement the other two parsers:

```python
def _fundamental_history_from_payload(value: object) -> list[FundamentalPeriod]:
    periods: list[FundamentalPeriod] = []
    for row in _as_list(value):
        if not isinstance(row, dict):
            continue
        report_date = _valid_iso_date(row.get("date"))
        if not report_date:
            continue
        try:
            periods.append(
                FundamentalPeriod(
                    date=report_date,
                    source=str(row.get("source") or ""),
                    revenue_yoy=_optional_float(row.get("revenue_yoy")),
                    net_profit_yoy=_optional_float(row.get("net_profit_yoy")),
                    roe=_optional_float(row.get("roe")),
                    gross_margin=_optional_float(row.get("gross_margin")),
                    debt_to_assets=_optional_float(row.get("debt_to_assets")),
                    ocf_to_profit=_optional_float(row.get("ocf_to_profit")),
                )
            )
        except (TypeError, ValueError):
            continue
    return sorted(periods, key=lambda item: item.date, reverse=True)


def _valuation_history_from_payload(value: object) -> list[ValuationPoint]:
    points: list[ValuationPoint] = []
    for row in _as_list(value):
        if not isinstance(row, dict):
            continue
        point_date = _valid_iso_date(row.get("date"))
        if not point_date:
            continue
        try:
            points.append(
                ValuationPoint(
                    date=point_date,
                    source=str(row.get("source") or ""),
                    pe_ttm=_optional_float(row.get("pe_ttm")),
                    pb=_optional_float(row.get("pb")),
                    ps=_optional_float(row.get("ps")),
                )
            )
        except (TypeError, ValueError):
            continue
    return sorted(points, key=lambda item: item.date, reverse=True)
```

Pass the parsed values into `MarketRawData` and `StockRawData`.

In `analysis.py`, pass `history=raw.history` when constructing `MarketSnapshot`.

- [ ] **Step 5: Run focused tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_data_sources_tdx_snapshot.py tests/test_market_regime.py tests/test_stock_research_memo.py
.venv/bin/ruff check src/stock_ts/models.py src/stock_ts/providers/tdx_snapshot_provider.py src/stock_ts/analysis.py tests/test_data_sources_tdx_snapshot.py
```

Expected: selected tests pass and ruff exits 0.

- [ ] **Step 6: Commit the typed contracts**

```bash
git add src/stock_ts/models.py src/stock_ts/providers/tdx_snapshot_provider.py src/stock_ts/analysis.py tests/test_data_sources_tdx_snapshot.py
git commit -m "feat: add typed cross-period research history"
```

## Task 2: Accumulate bounded market history

**Files:**
- Modify: `scripts/refresh_tdx_snapshot.py`
- Modify: `tests/test_tdx_snapshot_refresh_script.py`

- [ ] **Step 1: Write failing accumulation tests**

Import `date` and `timedelta` from `datetime`. Add tests for two refresh dates, duplicate replacement, malformed dates, and 60-row retention. Use these concrete helpers:

```python
def _market_payload(
    trade_date: str,
    *,
    advancing: int = 2200,
    declining: int = 2500,
) -> dict[str, object]:
    return {
        "trade_date": trade_date,
        "indices": [{"code": "000001", "name": "上证指数", "close": 3500, "pct_chg": 0.5, "amount": 5000}],
        "advancing": advancing,
        "declining": declining,
        "limit_up": 60,
        "limit_down": 12,
        "top_sectors": [],
    }


def test_refresh_snapshot_accumulates_market_history(tmp_path: Path) -> None:
    module = _load_refresh_module()
    output = tmp_path / "snapshot.json"
    output.write_text(
        json.dumps({"market": _market_payload("2026-07-09")}),
        encoding="utf-8",
    )

    def runner(operation: str, payload: dict[str, object], python_executable: str):
        if operation == "market":
            return _market_payload("2026-07-10", advancing=2700, declining=2100)
        if operation == "sectors":
            return {"sectors": []}
        if operation == "candidate_universe":
            return {"scanned_count": 0, "items": []}
        raise AssertionError(operation)

    module.refresh_snapshot(output, runner=runner, python_executable="python")

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [row["trade_date"] for row in payload["market_history"]] == [
        "2026-07-09",
        "2026-07-10",
    ]
    assert payload["market_history"][-1]["breadth_ratio"] == pytest.approx(2700 / 2100)


def test_market_history_deduplicates_and_keeps_latest_60_rows() -> None:
    module = _load_refresh_module()
    start = date(2026, 4, 1)
    rows = [_market_payload((start + timedelta(days=offset)).isoformat()) for offset in range(70)]
    rows.append(_market_payload(rows[-1]["trade_date"], advancing=3000, declining=1000))

    result = module._merge_market_history(rows, limit=60)

    assert len(result) == 60
    assert result[-1]["trade_date"] == rows[-1]["trade_date"]
    assert result[-1]["advancing"] == 3000
```

- [ ] **Step 2: Run tests and confirm `market_history` is not written**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_tdx_snapshot_refresh_script.py
```

Expected: FAIL because `_merge_market_history` and the output block do not exist.

- [ ] **Step 3: Implement normalization, deduplication, and retention**

Import `date` from `datetime` and add:

```python
def _market_history_row(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    trade_date = str(value.get("trade_date") or "").strip()[:10]
    try:
        date.fromisoformat(trade_date)
        advancing = int(value.get("advancing", 0))
        declining = int(value.get("declining", 0))
    except (TypeError, ValueError):
        return None
    if advancing < 0 or declining <= 0:
        return None
    try:
        if value.get("amount") not in {None, ""}:
            amount = float(value["amount"])
        else:
            indices = value.get("indices") if isinstance(value.get("indices"), list) else []
            amount = sum(
                float(item.get("amount", 0.0))
                for item in indices
                if isinstance(item, dict) and float(item.get("amount", 0.0)) > 0
            )
    except (TypeError, ValueError):
        return None
    return {
        "trade_date": trade_date,
        "advancing": advancing,
        "declining": declining,
        "breadth_ratio": round(advancing / max(declining, 1), 4),
        "limit_up": int(value.get("limit_up", 0)),
        "limit_down": int(value.get("limit_down", 0)),
        "amount": round(amount, 4),
    }


def _merge_market_history(*values: object, limit: int = 60) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for value in values:
        rows = value if isinstance(value, list) else [value]
        for row in rows:
            normalized = _market_history_row(row)
            if normalized:
                by_date[normalized["trade_date"]] = normalized
    return [by_date[key] for key in sorted(by_date)][-limit:]
```

Before building `snapshot`, compute:

```python
market_history = _merge_market_history(
    existing.get("market_history", []),
    existing.get("market"),
    market,
)
```

Write `"market_history": market_history` into the new snapshot.

- [ ] **Step 4: Run refresh tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_tdx_snapshot_refresh_script.py
.venv/bin/ruff check scripts/refresh_tdx_snapshot.py tests/test_tdx_snapshot_refresh_script.py
```

Expected: all selected tests pass and ruff exits 0.

- [ ] **Step 5: Commit market accumulation**

```bash
git add scripts/refresh_tdx_snapshot.py tests/test_tdx_snapshot_refresh_script.py
git commit -m "feat: accumulate bounded market history"
```

## Task 3: Preserve financial and valuation history during enrichment

**Files:**
- Modify: `scripts/enrich_tdx_snapshot.py`
- Modify: `tests/test_external_snapshot_enrichment.py`

- [ ] **Step 1: Write failing financial-history tests**

Extend the existing fake adapters with multi-period subclasses, then assert the enriched stock keeps the newest flat block plus all normalized periods:

```python
class MultiPeriodTushare(RichTushare):
    def fina_indicator(self, ts_code: str, limit: int, fields: str) -> MiniFrame:
        assert limit == 8
        return MiniFrame(
            [
                {"end_date": "20260331", "or_yoy": 18, "netprofit_yoy": 24, "roe": 16},
                {"end_date": "20251231", "or_yoy": 14, "netprofit_yoy": 19, "roe": 15},
                {"end_date": "20250930", "or_yoy": 10, "netprofit_yoy": 13, "roe": 14},
            ]
        )


def test_tushare_enrichment_keeps_multiple_financial_periods(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)
    module.enrich_snapshot(
        snapshot,
        codes=["688362"],
        ak=TushareOnlyAk(),
        tushare_client=MultiPeriodTushare(),
        market_news_limit=0,
    )
    stock = json.loads(snapshot.read_text(encoding="utf-8"))["stocks"]["688362"]

    assert stock["fundamental_metrics"]["date"] == "2026-03-31"
    assert [row["date"] for row in stock["fundamental_history"]] == [
        "2026-03-31",
        "2025-12-31",
        "2025-09-30",
    ]
```

Add the AKShare fallback fixture and assertion:

```python
class MultiPeriodFinancialFallbackAk(FinancialFallbackAk):
    def stock_financial_analysis_indicator_em(
        self, symbol: str = "301389.SZ", indicator: str = "按报告期"
    ) -> MiniFrame:
        base = super().stock_financial_analysis_indicator_em(symbol, indicator)._rows[0]
        return MiniFrame(
            [
                dict(base, REPORT_DATE="2026-03-31 00:00:00", TOTALOPERATEREVETZ=18, PARENTNETPROFITTZ=24),
                dict(base, REPORT_DATE="2025-12-31 00:00:00", TOTALOPERATEREVETZ=14, PARENTNETPROFITTZ=19),
                dict(base, REPORT_DATE="2025-09-30 00:00:00", TOTALOPERATEREVETZ=10, PARENTNETPROFITTZ=13),
            ]
        )


def test_akshare_fallback_keeps_multiple_financial_periods(tmp_path: Path) -> None:
    module = _load_enrichment_module()
    snapshot = tmp_path / "tdx.json"
    _write_snapshot(snapshot)
    module.enrich_snapshot(
        snapshot,
        codes=["688362"],
        ak=MultiPeriodFinancialFallbackAk(),
        tushare_client=RestrictedTushare(),
        market_news_limit=0,
    )
    stock = json.loads(snapshot.read_text(encoding="utf-8"))["stocks"]["688362"]
    assert [row["date"] for row in stock["fundamental_history"]] == [
        "2026-03-31",
        "2025-12-31",
        "2025-09-30",
    ]
```

- [ ] **Step 2: Write failing valuation-history tests**

```python
def test_valuation_history_merges_dates_and_retains_250_points() -> None:
    module = _load_enrichment_module()
    existing = [
        {"date": f"2025-{month:02d}-01", "source": "old", "pe_ttm": 10 + month}
        for month in range(1, 13)
    ]
    merged = module._merge_dated_history(
        existing,
        {"date": "2025-12-01", "source": "new", "pe_ttm": 30},
        {"date": "2026-01-02", "source": "new", "pe_ttm": 31},
        limit=250,
    )

    assert merged[0]["date"] == "2026-01-02"
    assert next(row for row in merged if row["date"] == "2025-12-01")["pe_ttm"] == 30
```

Add a generated 260-valid-date case and assert only the newest 250 remain.

- [ ] **Step 3: Run tests and confirm history blocks are absent**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_external_snapshot_enrichment.py
```

Expected: the new tests fail because enrichment only stores the latest rows.

- [ ] **Step 4: Normalize up to eight financial periods**

Import `date` from `datetime` in `scripts/enrich_tdx_snapshot.py` for strict report-date validation.

Create the two history fetchers using one upstream call each:

```python
def _fetch_tushare_fina_history(ts_client: object, code: str) -> list[dict[str, Any]]:
    frame = ts_client.fina_indicator(  # type: ignore[attr-defined]
        ts_code=_tushare_code(code),
        limit=8,
        fields=(
            "ts_code,end_date,or_yoy,netprofit_yoy,roe,grossprofit_margin,"
            "debt_to_assets,ocf_to_profit"
        ),
    )
    normalized = [
        {
            "source": "tushare.fina_indicator",
            "date": _format_tushare_date(str(row.get("end_date") or "")),
            "revenue_yoy": _optional_float(row.get("or_yoy")),
            "net_profit_yoy": _optional_float(row.get("netprofit_yoy")),
            "roe": _optional_float(row.get("roe")),
            "gross_margin": _optional_float(row.get("grossprofit_margin")),
            "debt_to_assets": _optional_float(row.get("debt_to_assets")),
            "ocf_to_profit": _optional_float(row.get("ocf_to_profit")),
        }
        for row in _records(frame)
    ]
    return _merge_dated_history(normalized, limit=8)


def _fetch_akshare_financial_history(ak: object, code: str) -> list[dict[str, Any]]:
    frame = ak.stock_financial_analysis_indicator_em(  # type: ignore[attr-defined]
        symbol=_akshare_em_symbol(code), indicator="按报告期"
    )
    normalized = [
        {
            "source": "akshare.stock_financial_analysis_indicator_em",
            "date": _format_report_date(str(row.get("REPORT_DATE") or "")),
            "revenue_yoy": _optional_float(row.get("TOTALOPERATEREVETZ")),
            "net_profit_yoy": _optional_float(row.get("PARENTNETPROFITTZ")),
            "roe": _optional_float(row.get("ROEJQ")),
            "gross_margin": _optional_float(row.get("XSMLL")),
            "debt_to_assets": _optional_float(row.get("ZCFZL")),
            "ocf_to_profit": None,
        }
        for row in _records(frame)[:8]
    ]
    return _merge_dated_history(normalized, limit=8)
```

In `_enrich_stock_payload`, replace the single-row financial fetch with:

```python
history = _fetch_tushare_fina_history(tushare_client, code)
if history:
    payload["fundamental_history"] = _merge_dated_history(
        payload.get("fundamental_history", []),
        payload.get("fundamental_metrics"),
        history,
        limit=8,
    )
    payload["fundamental_metrics"] = payload["fundamental_history"][0]
```

In the AKShare fallback block use this exact branch:

```python
if not payload.get("fundamental_history"):
    history = _fetch_akshare_financial_history(ak, code)
    if history:
        payload["fundamental_history"] = _merge_dated_history(
            payload.get("fundamental_history", []),
            payload.get("fundamental_metrics"),
            history,
            limit=8,
        )
        payload["fundamental_metrics"] = payload["fundamental_history"][0]
```

- [ ] **Step 5: Add the shared dated-history merge and valuation accumulation**

Implement:

```python
def _merge_dated_history(*values: object, limit: int) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for value in values:
        rows = value if isinstance(value, list) else [value]
        for row in rows:
            if not isinstance(row, dict):
                continue
            normalized = dict(row)
            report_date = _format_report_date(str(normalized.get("date") or ""))
            try:
                date.fromisoformat(report_date)
            except ValueError:
                continue
            normalized["date"] = report_date
            by_date[report_date] = normalized
    return [by_date[key] for key in sorted(by_date, reverse=True)[:limit]]
```

Whenever a valuation fetch succeeds, preserve the previous valuation before overwriting and set:

```python
payload["valuation_history"] = _merge_dated_history(
    payload.get("valuation_history", []),
    previous_valuation,
    valuation,
    limit=250,
)
payload["valuation"] = valuation
```

- [ ] **Step 6: Run enrichment tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_external_snapshot_enrichment.py
.venv/bin/ruff check scripts/enrich_tdx_snapshot.py tests/test_external_snapshot_enrichment.py
```

Expected: all selected tests pass and ruff exits 0.

- [ ] **Step 7: Commit enrichment history**

```bash
git add scripts/enrich_tdx_snapshot.py tests/test_external_snapshot_enrichment.py
git commit -m "feat: preserve financial and valuation history"
```

## Task 4: Use market history in regime evidence

**Files:**
- Modify: `src/stock_ts/research/market_regime.py`
- Modify: `tests/test_market_regime.py`
- Modify: `tests/test_web_market_research_workspace.py`

- [ ] **Step 1: Write failing minimum-sample tests**

Import `replace` from `dataclasses` and `MarketHistoryPoint` from `stock_ts.models`. Add these deterministic fixtures and assertions:

```python
def _history(count: int) -> list[MarketHistoryPoint]:
    return [
        MarketHistoryPoint(
            trade_date=f"2026-07-{8 + index:02d}",
            advancing=1800 + index * 250,
            declining=2800 - index * 200,
            breadth_ratio=(1800 + index * 250) / (2800 - index * 200),
            limit_up=45 + index * 5,
            limit_down=25 - index * 3,
            amount=9000 + index * 500,
        )
        for index in range(count)
    ]


def _market_with_history(
    history: list[MarketHistoryPoint],
    *,
    heat: int = 58,
    limit_down: int = 12,
):
    return replace(
        _market(heat=heat, advancing=2600, declining=2300, limit_down=limit_down),
        history=history,
    )


def test_one_market_history_point_keeps_single_day_limitations() -> None:
    result = assess_market_regime(_market_with_history(_history(1)))
    breadth = next(item for item in result.dimensions if item.name == "宽度")
    liquidity = next(item for item in result.dimensions if item.name == "流动性")
    assert breadth.status == EvidenceStatus.DEGRADED
    assert liquidity.status == EvidenceStatus.DEGRADED
    assert "仅有当日截面" in breadth.evidence


def test_three_market_history_points_create_cross_period_evidence() -> None:
    result = assess_market_regime(_market_with_history(_history(3)))
    breadth = next(item for item in result.dimensions if item.name == "宽度")
    liquidity = next(item for item in result.dimensions if item.name == "流动性")
    assert breadth.status == EvidenceStatus.COMPLETE
    assert liquidity.status == EvidenceStatus.COMPLETE
    assert "近 3 个交易日" in breadth.evidence
    assert "流动性代理" in liquidity.evidence


def test_positive_history_never_overrides_current_extreme_risk() -> None:
    result = assess_market_regime(
        _market_with_history(_history(5), heat=60, limit_down=80)
    )
    assert result.stage == "风险释放"
    assert result.risk_budget == "10%-30%"
```

Add a renderer assertion that `近 3 个交易日` appears in market workspace HTML.

- [ ] **Step 2: Run tests and confirm dimensions remain single-day**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_market_regime.py tests/test_web_market_research_workspace.py
```

Expected: the new history assertions fail.

- [ ] **Step 3: Derive recent market-history evidence**

Add helpers:

```python
def _recent_history(market: MarketSnapshot) -> tuple[MarketHistoryPoint, ...]:
    return tuple(sorted(market.history, key=lambda item: item.trade_date)[-5:])


def _direction(first: float, last: float, *, tolerance: float = 0.05) -> str:
    if last > first + tolerance:
        return "改善"
    if last < first - tolerance:
        return "回落"
    return "平稳"


def _history_depth_bonus(market: MarketSnapshot) -> int:
    count = len(_recent_history(market))
    if count >= 5:
        return 8
    if count >= 3:
        return 4
    return 0
```

Pass recent history into `_dimensions`. For fewer than three points, make width and liquidity degraded and keep `仅有当日截面` or `短样本`. For at least three points, include first/last breadth, amount proxy, and limit-down counts in evidence and mark width/liquidity complete.

Add `_history_depth_bonus` to confidence before bounding it, while keeping `_contradiction_penalty` and Phase 1 `_classify` order unchanged.

- [ ] **Step 4: Run market research tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_market_regime.py tests/test_web_market_research_workspace.py
.venv/bin/ruff check src/stock_ts/research/market_regime.py tests/test_market_regime.py tests/test_web_market_research_workspace.py
```

Expected: selected tests pass and ruff exits 0.

- [ ] **Step 5: Commit market cross-period evidence**

```bash
git add src/stock_ts/research/market_regime.py tests/test_market_regime.py tests/test_web_market_research_workspace.py
git commit -m "feat: add cross-period market regime evidence"
```

## Task 5: Use financial and valuation history in the stock memo

**Files:**
- Modify: `src/stock_ts/research/stock_memo.py`
- Modify: `tests/test_stock_research_memo.py`
- Modify: `tests/test_web_stock_research_workspace.py`

- [ ] **Step 1: Write failing financial-trend tests**

Import `FundamentalPeriod` and `ValuationPoint` from `stock_ts.models`. Add these typed fixtures and assertions:

```python
def _fundamental_history(values: list[tuple[float, float]]) -> list[FundamentalPeriod]:
    dates = ["2025-09-30", "2025-12-31", "2026-03-31"][-len(values):]
    return [
        FundamentalPeriod(
            date=period_date,
            source="fixture",
            revenue_yoy=revenue,
            net_profit_yoy=profit,
            roe=12 + index,
            gross_margin=30 + index,
            debt_to_assets=45 - index,
            ocf_to_profit=1 + index / 10,
        )
        for index, (period_date, (revenue, profit)) in enumerate(zip(dates, values))
    ][::-1]


def _valuation_history(count: int) -> list[ValuationPoint]:
    return [
        ValuationPoint(
            date=f"2026-06-{index + 1:02d}",
            source="fixture",
            pe_ttm=10 + index,
            pb=2.0,
            ps=3.0,
        )
        for index in range(count)
    ]


def test_one_financial_period_never_claims_trend() -> None:
    memo = build_stock_research_memo(
        _raw_stock(fundamental_history=_fundamental_history([(12, 18)]))
    )
    assert "连续改善" not in memo.quality.conclusion
    assert "1 期" in memo.quality.limitations


def test_three_improving_periods_support_improvement_statement() -> None:
    memo = build_stock_research_memo(
        _raw_stock(fundamental_history=_fundamental_history([(8, 9), (12, 14), (18, 24)]))
    )
    assert "连续改善" in memo.quality.conclusion
    assert "财务 3 期" in next(
        item.detail for item in memo.evidence if item.block == "经营质量"
    )


def test_revenue_profit_divergence_is_not_called_overall_improvement() -> None:
    memo = build_stock_research_memo(
        _raw_stock(fundamental_history=_fundamental_history([(18, 8), (14, 12), (10, 20)]))
    )
    assert "分化" in memo.quality.conclusion
    assert "连续改善" not in memo.quality.conclusion
```

- [ ] **Step 2: Write failing valuation-threshold tests**

```python
def test_nineteen_pe_points_do_not_create_history_percentile() -> None:
    memo = build_stock_research_memo(
        _raw_stock(valuation_history=_valuation_history(19), valuation={"pe_ttm": 18})
    )
    assert "历史积累中 19/20" in memo.valuation.limitations
    assert "历史分位" not in memo.valuation.conclusion


def test_twenty_pe_points_create_descriptive_history_percentile() -> None:
    memo = build_stock_research_memo(
        _raw_stock(valuation_history=_valuation_history(20), valuation={"pe_ttm": 18})
    )
    assert "20 个观察点" in memo.valuation.conclusion
    assert "低估" not in memo.valuation.conclusion
```

Add a stale-input test with complete history and assert `数据暂停 / 0` still wins. Add renderer assertions for `财务 3 期` and `20 个观察点`.

- [ ] **Step 3: Run tests and confirm stock memo ignores history**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_stock_research_memo.py tests/test_web_stock_research_workspace.py
```

Expected: new trend and valuation assertions fail.

- [ ] **Step 4: Implement effective valuation context**

Add:

```python
def _effective_valuation(raw: StockRawData) -> tuple[dict[str, object], int]:
    valuation: dict[str, object] = dict(raw.valuation)
    valid_points = [
        item.pe_ttm
        for item in raw.valuation_history
        if item.pe_ttm is not None and math.isfinite(item.pe_ttm) and item.pe_ttm > 0
    ]
    explicit = _number(valuation.get("pe_percentile"))
    current = raw.pe_ttm if raw.pe_ttm is not None else _number(valuation.get("pe_ttm"))
    if explicit is None and current is not None and current > 0 and len(valid_points) >= 20:
        valuation["pe_percentile"] = (
            sum(point <= current for point in valid_points) / len(valid_points) * 100
        )
        valuation["pe_percentile_basis"] = len(valid_points)
    return valuation, len(valid_points)
```

Use the effective mapping in both quality-gate derivation and `_valuation_section`. If the percentile basis is internal, say `基于 N 个观察点的 PE 历史分位` rather than implying a provider-supplied long history. With fewer than 20 valid points, append `估值历史积累中 N/20` to limitations.

- [ ] **Step 5: Implement financial-period trend evidence**

Pass `raw.fundamental_history` into `_quality_section`. Sort newest first, use the latest three periods, and compare chronological revenue/profit sequences. Convert the newest typed period into a metric mapping when the legacy flat block is empty:

```python
def _period_metrics(period: FundamentalPeriod) -> dict[str, float | str | None]:
    return {
        "date": period.date,
        "source": period.source,
        "revenue_yoy": period.revenue_yoy,
        "net_profit_yoy": period.net_profit_yoy,
        "roe": period.roe,
        "gross_margin": period.gross_margin,
        "debt_to_assets": period.debt_to_assets,
        "ocf_to_profit": period.ocf_to_profit,
    }


history = sorted(raw.fundamental_history, key=lambda item: item.date, reverse=True)
quality_metrics = raw.fundamental_metrics or (_period_metrics(history[0]) if history else {})
```

Use `quality_metrics` in `_quality_section` and in `fundamental_metric_coverage` so typed history and the legacy latest block cannot disagree.

Use the latest three periods and compare chronological revenue/profit sequences:

```python
def _strict_direction(values: list[float]) -> str:
    if len(values) < 3:
        return "insufficient"
    if all(current > previous for previous, current in zip(values, values[1:])):
        return "improving"
    if all(current < previous for previous, current in zip(values, values[1:])):
        return "weakening"
    return "mixed"
```

Use `连续改善` only when both revenue and profit are improving. Use `连续走弱` only when both weaken. If directions differ, output `收入与利润增速分化`. For two periods, state `较上一期变化`; for one period, retain single-period limitations.

Change the operating-quality evidence detail to include `财务 N 期`. Treat three or more valid periods as complete evidence when the latest metric coverage is complete; otherwise keep degraded. Pass `fundamental_period_count` into `_verdict` and calculate:

```python
depth_bonus = min(6, max(0, fundamental_period_count - 2) * 2)
confidence = max(25, min(100, 78 - missing_count * 18 + depth_bonus))
```

Return the Phase 1 stale verdict before applying the bonus.

- [ ] **Step 6: Run stock research tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_research_evidence.py tests/test_stock_research_memo.py tests/test_web_stock_research_workspace.py
.venv/bin/ruff check src/stock_ts/research/stock_memo.py tests/test_stock_research_memo.py tests/test_web_stock_research_workspace.py
```

Expected: selected tests pass and ruff exits 0.

- [ ] **Step 7: Commit stock cross-period evidence**

```bash
git add src/stock_ts/research/stock_memo.py tests/test_stock_research_memo.py tests/test_web_stock_research_workspace.py
git commit -m "feat: add cross-period stock research evidence"
```

## Task 6: Verify, document, and deploy Phase 2

**Files:**
- Create: `docs/research/research-data-depth-test-report.md`

- [ ] **Step 1: Run focused and full local verification**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_data_sources_tdx_snapshot.py \
  tests/test_tdx_snapshot_refresh_script.py \
  tests/test_external_snapshot_enrichment.py \
  tests/test_market_regime.py \
  tests/test_stock_research_memo.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_stock_research_workspace.py
.venv/bin/ruff check src tests scripts
PYTHONPATH=src .venv/bin/pytest -q
```

Expected: focused tests and ruff pass. Full pytest has no failures beyond the recorded five daily-pipeline failures and one stale-copy assertion.

- [ ] **Step 2: Create a temporary history-rich snapshot and run local Web smoke**

Copy a fixture snapshot into a temporary directory, populate three market-history rows, three financial periods, and twenty valuation points for the selected stock, then run the Web app on an unused port using `STOCK_TS_TDX_SNAPSHOT_PATH` and authentication disabled only for the preview. Verify HTTP 200 and search the response for `近 3 个交易日`, `财务 3 期`, and `20 个观察点`. Stop the process.

- [ ] **Step 3: Write and commit the local report**

Record branch, source commit, Python version, focused/full counts, baseline comparison, lint output, local HTTP evidence, and known failures in `docs/research/research-data-depth-test-report.md`, then commit:

```bash
git add docs/research/research-data-depth-test-report.md
git commit -m "docs: record research data depth verification"
```

- [ ] **Step 4: Deploy a source-only incremental patch**

Compare remote hashes with the Phase 1 deployed hashes. Generate a patch containing only changed `src/stock_ts` and `scripts` files. Upload it, run remote `git apply --check`, create a timestamped archive under `/opt/stock-ts/.deploy_backups/`, apply the patch, and explicitly compile every changed Python file.

Do not overwrite `.env`, snapshots, holdings, accounts, reports, Nginx, timers, or DSA. The schema is forward-compatible, so existing production snapshot data remains untouched until the normal pipeline next refreshes it.

- [ ] **Step 5: Verify preview, service, public route, and rollback artifact**

On the server:

1. create a temporary copy of the production snapshot and inject history-rich fixture rows into the copy only;
2. start a read-only, authentication-disabled preview on `127.0.0.1:18501` pointing at the copy;
3. verify HTTP 200 plus the three cross-period markers;
4. stop the preview and confirm port 18501 is released;
5. restart `stock-ts.service` and confirm a new PID plus active state;
6. verify the protected public root redirects to login and the public login page returns 200;
7. list the backup archive and compare streamed pre-deploy hashes with the recorded baseline.

- [ ] **Step 6: Update and commit deployment evidence**

Add the exact remote backup path, patch check, compile behavior, preview markers, service PID, public route status, and rollback hashes to the report, then commit:

```bash
git add docs/research/research-data-depth-test-report.md
git commit -m "docs: record research data depth deployment"
```
