# Research Data Depth Design

**Date:** 2026-07-13  
**Scope:** Phase 2 of the StockTs system upgrade  
**Status:** Approved under the user's instruction to continue the recommended data-depth phase autonomously

## 1. Purpose

Phase 1 prevents stale or incomplete inputs from producing authoritative conclusions. Phase 2 makes valid conclusions deeper by preserving and consuming cross-period evidence.

The current runtime has three structural limitations:

1. Each market refresh replaces the previous market snapshot, so market breadth, turnover, and extreme-risk changes cannot be measured across days.
2. Tushare and AKShare financial endpoints can return multiple report periods, but enrichment stores only the latest row.
3. Each valuation refresh replaces the previous valuation object, so the application cannot build its own historical percentile.

This phase adds backward-compatible history arrays to the existing JSON snapshot. It does not introduce a database, migrate user data, add a paid provider, or claim long-term trends before enough observations exist.

## 2. Options Considered

### Option A: Derive more indicators from current K-line data

This can add moving averages, volatility, and momentum quickly. It does not solve single-period fundamentals or single-day market breadth, so the research would remain technically detailed but economically shallow. Rejected as the main Phase 2 approach.

### Option B: Accumulate history in the current JSON snapshot

Preserve daily market context, multiple financial report periods, and daily valuation points inside the existing snapshot. Add typed provider contracts and let research models use the history only after explicit minimum-sample checks. Selected because it produces real cross-period evidence while preserving the current deployment and pipeline shape.

### Option C: Move research history to SQLite and Parquet

This is the long-term storage direction, especially for full-market history and backtests. It would require schema migrations, retention jobs, transaction semantics, and a cache rollout. Rejected for Phase 2 because it combines infrastructure migration with research-model changes.

## 3. Snapshot Schema

All new blocks are optional. Old snapshots remain readable.

### 3.1 Market history

Add a top-level `market_history` array:

```json
[
  {
    "trade_date": "2026-07-13",
    "advancing": 2600,
    "declining": 2200,
    "breadth_ratio": 1.1818,
    "limit_up": 72,
    "limit_down": 11,
    "amount": 10452.3
  }
]
```

Rules:

- `refresh_tdx_snapshot.py` appends both the previous valid market object and the newly fetched market object before replacing `market`.
- Deduplicate by ISO trade date, keep the newest value for a duplicate date, sort ascending, and retain the most recent 60 sessions.
- Ignore non-date placeholders such as `latest` and rows without valid breadth counts.
- `amount` is the sum of positive index `amount` values and is explicitly a major-index liquidity proxy, not total A-share turnover.

### 3.2 Fundamental history

Add `fundamental_history` to each stock:

```json
[
  {
    "source": "tushare.fina_indicator",
    "date": "2026-03-31",
    "revenue_yoy": 12.4,
    "net_profit_yoy": 18.1,
    "roe": 9.2,
    "gross_margin": 31.0,
    "debt_to_assets": 42.0,
    "ocf_to_profit": 1.1
  }
]
```

Rules:

- Tushare and AKShare adapters request and normalize up to eight report periods in one upstream call.
- Deduplicate by report date, sort newest first, and retain eight periods.
- The newest normalized row continues to populate legacy `fundamental_metrics` for compatibility.
- Existing history is preserved if a provider call fails.
- Missing fields remain `null`; they are never forward-filled from another period.
- Hong Kong/Yahoo history is outside this phase; its current latest-value behavior remains unchanged and visibly degraded.

### 3.3 Valuation history

Add `valuation_history` to each stock:

```json
[
  {
    "source": "tushare.daily_basic",
    "date": "2026-07-13",
    "pe_ttm": 18.2,
    "pb": 2.4,
    "ps": 3.1
  }
]
```

Rules:

- Each successful enrichment merges the previous and current valuation objects into history.
- Deduplicate by date, sort newest first, and retain 250 valid points.
- Only finite positive PE/PB/PS values participate in percentile calculations; negative PE is retained for audit only but excluded from PE percentile ranking.
- A historical PE percentile is produced only with at least 20 valid PE observations.
- Existing explicit provider percentiles remain authoritative when valid.

## 4. Typed Domain Contracts

Add immutable models:

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

Extend existing models with default-empty history fields:

- `MarketRawData.history`
- `MarketSnapshot.history`
- `StockRawData.fundamental_history`
- `StockRawData.valuation_history`

Defaults preserve every existing caller and provider.

## 5. Market Research Behavior

`assess_market_regime` keeps the Phase 1 risk-first classification. History changes evidence depth and confidence, not the safety ordering.

### 5.1 Minimum samples

- 0-1 points: retain `仅有当日截面`; trend/liquidity dimensions remain degraded.
- 2 points: show an explicit day-over-day comparison, still label it `短样本` and keep the dimension degraded.
- 3 or more points: calculate recent breadth direction and liquidity-proxy direction; the corresponding dimensions can become complete.
- Use at most the latest five sessions in display text so stale older history does not dominate current regime evidence.

### 5.2 Derived evidence

- Breadth direction compares the first and last breadth ratio in the recent window.
- Liquidity direction compares the first and last positive amount proxy.
- Extreme-risk direction compares limit-down counts and identifies expansion, contraction, or stability.
- No history block may override a current hard risk-release condition.
- Confidence receives at most an eight-point depth bonus and remains bounded from 0 to 100. Contradiction penalties still apply after the depth bonus.

## 6. Stock Research Behavior

### 6.1 Fundamental trend

- One valid period: describe a current snapshot only.
- Two valid periods: describe direction as `较上一期变化`, not a durable trend.
- Three or more valid periods: allow `连续改善`, `连续走弱`, or `分化` only when the same metric is valid in all compared periods.
- Revenue and net-profit growth are evaluated separately; improving profit with weakening revenue is labeled divergence, not overall improvement.
- Cash-flow, leverage, ROE, and margin remain facts unless their own multi-period values are available.

### 6.2 Valuation context

- Use a valid provider percentile first.
- Otherwise compute PE percentile from `valuation_history` only when at least 20 positive finite observations exist.
- Fewer than 20 observations display `估值历史积累中 N/20` and keep valuation evidence degraded.
- Percentile language remains descriptive. It does not produce `低估`, `高估`, or a buy action by itself.

### 6.3 Confidence and audit

- Fundamental availability still requires real metric values, as established in Phase 1.
- Three or more report periods can improve evidence status and add at most six confidence points.
- A single period cannot receive the depth bonus.
- Evidence detail states the exact number of financial periods and valuation observations used.
- Stale quote status still forces `数据暂停 / 0`, regardless of historical depth.

## 7. Web Presentation

No new dashboard is introduced. Existing research cards surface depth through their structured evidence:

- Market width and liquidity cards show `近 N 个交易日` comparisons.
- Stock operating-quality facts show report-period changes when supported.
- Valuation limitations show the observation count or the computed percentile basis.
- Evidence audit rows include `财务 N 期` and `估值 N 点`.

This keeps the current professional hierarchy and avoids adding another equal-weight panel.

## 8. Failure Handling and Compatibility

- A failed history refresh does not erase existing history or the latest legacy block.
- Malformed history rows are ignored individually; one bad row does not block the stock or market page.
- Duplicate dates resolve deterministically to the newest payload.
- All limits are enforced before writing the snapshot to prevent unbounded JSON growth.
- Providers other than `tdx-snapshot` continue returning empty history and retain current behavior.
- History remains on the canonical `stocks[code]` payload. This phase does not duplicate multi-period history across all candidate-universe rows.

## 9. Tests and Acceptance Criteria

### 9.1 Snapshot and provider tests

1. Two refreshes produce deduplicated market history in ascending date order.
2. Market history keeps at most 60 valid sessions.
3. Tushare and AKShare financial normalization preserves up to eight report periods.
4. Valuation merge deduplicates dates and keeps at most 250 points.
5. Old snapshots without history still load unchanged.
6. Malformed history rows are ignored without breaking valid rows.

### 9.2 Research tests

1. One market point retains single-day limitations.
2. Three market points produce cross-period breadth and liquidity evidence.
3. Current extreme downside risk still overrides positive history.
4. One financial period cannot claim a trend.
5. Three improving periods produce a supported improvement statement.
6. Divergent revenue/profit sequences produce a divergence statement.
7. Nineteen PE points do not create a percentile; twenty valid points do.
8. Stale quotes remain `数据暂停 / 0` even with complete history.

### 9.3 Regression and deployment

- Focused snapshot/provider/research/Web tests pass.
- Full ruff passes.
- Full pytest introduces no failures beyond the recorded six-failure baseline.
- A local and remote temporary preview visibly renders cross-period evidence from a fixture snapshot.
- Deployment uses a source-only patch, timestamped backup, explicit compile/import checks, service restart, protected public-route verification, and archive integrity verification.

## 10. Non-Goals

- No SQLite/Parquet migration.
- No backfill of 60 market sessions or 250 valuation sessions from a new external endpoint.
- No analyst-consensus forecasts, target prices, or paid research ingestion.
- No automatic trading or broker integration.
- No rewrite of the existing 13,000-line Web orchestration file.
