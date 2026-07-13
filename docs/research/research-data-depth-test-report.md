# Research Data Depth Test Report

**Date:** 2026-07-13  
**Branch:** `codex/research-data-depth`  
**Source commit tested:** `e8eb87d`  
**Scope:** Phase 2 cross-period research evidence

## 1. Result

Phase 2 passes the focused history/provider/research suite and full ruff. The full pytest suite retains the same six failures as the Phase 1 baseline and introduces no new failure.

| Check | Before | After | Result |
| --- | ---: | ---: | --- |
| Focused Phase 2 tests | 63 passed | 82 passed | Pass |
| Full pytest | 478 passed, 6 failed, 11 warnings | 497 passed, 6 failed, 11 warnings | No new failures |
| Full ruff | All checks passed | All checks passed | Pass |
| History-rich local HTTP GET | Not applicable | 200, 297330 bytes | Pass |

The 19 additional passing tests cover typed history parsing, market accumulation, financial and valuation retention, minimum-sample research rules, and Web visibility.

## 2. Environment

- Worktree: `/Users/fangjie/.config/superpowers/worktrees/StockTs/codex-research-data-depth`
- Python: 3.11.15
- pytest: 9.1.1
- ruff: 0.15.16
- Local ignored runtime data is linked from the primary checkout. Verification never modifies the real holdings, production snapshot, accounts, or reports.

## 3. Focused Verification

Command:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_data_sources_tdx_snapshot.py \
  tests/test_tdx_snapshot_refresh_script.py \
  tests/test_external_snapshot_enrichment.py \
  tests/test_market_regime.py \
  tests/test_stock_research_memo.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_stock_research_workspace.py
```

Result:

```text
82 passed in 1.61s
```

Verified behavior:

- old snapshots load with empty history;
- malformed history rows are isolated and ignored;
- market history is date-deduplicated and limited to 60 sessions;
- Tushare and AKShare retain up to eight report periods;
- valuation history is date-deduplicated and limited to 250 points;
- one market point stays single-day, while three points produce cross-period evidence;
- positive history cannot override current extreme downside risk;
- one financial period cannot claim a trend;
- three consistent periods can support improvement or weakening language;
- revenue/profit disagreement is labeled divergence;
- PE percentile requires at least 20 unique positive observations;
- stale quote status still forces `数据暂停 / 0`.

## 4. Lint

Command:

```bash
/Users/fangjie/Documents/StockTs/.venv/bin/ruff check src tests scripts
```

Result:

```text
All checks passed!
```

## 5. Full Suite

Command:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Result:

```text
6 failed, 497 passed, 11 warnings in 12.83s
```

Unchanged baseline failures:

1. `tests/test_daily_pipeline.py::test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
2. `tests/test_daily_pipeline.py::test_daily_pipeline_continues_when_external_enrichment_times_out`
3. `tests/test_daily_pipeline.py::test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
4. `tests/test_daily_pipeline.py::test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
5. `tests/test_daily_pipeline.py::test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`
6. `tests/test_web_data_accuracy.py::test_web_blocks_opportunity_ranking_when_snapshot_trade_date_is_stale`

## 6. Local History-Rich Web Smoke

A temporary copy of the real market snapshot was enriched only in `/tmp` with:

- three market-history sessions;
- three financial report periods for `603278`;
- twenty unique valuation observations for `603278`.

Preview environment:

```text
PORT=18503
STOCK_TS_AUTH_ENABLED=0
STOCK_TS_PUBLIC_READONLY=1
STOCK_TS_NOW=2026-07-11T09:30:00+08:00
STOCK_TS_TDX_SNAPSHOT_PATH=/tmp/stockts-data-depth-preview.json
```

GET evidence:

```text
http_status=200
response_bytes=297330
近 3 个交易日=4
财务 3 期=3
基于 20 个观察点=1
连续改善=3
data-market-stage="风险释放"
data-research-status="条件研究"
```

The current fixture market has an extreme limit-down signal, so `风险释放` correctly remains active despite improving history. The temporary server was stopped after the check.

## 7. Deployment Verification

Status: pending incremental server deployment.

The deployment record must add the remote baseline hashes, patch-check result, backup path, explicit compile/import behavior, temporary history-rich preview markers, service PID transition, protected public-route status, and rollback archive hashes.
