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

Status: deployed and verified on 2026-07-13.

Deployment target:

```text
host=47.82.145.207
application=/opt/stock-ts
service=stock-ts.service
public_url=https://stock.jiewat-kaka-fj.com/
```

The incremental source patch contained seven Python files (42,605 bytes; 619 insertions and 94 deletions). `git apply --check` passed before the patch was applied. The production `.env`, market snapshot, holdings, accounts, reports, Nginx configuration, timers, and separate DSA service were preserved.

Rollback material:

```text
backup=/opt/stock-ts/.deploy_backups/research-data-depth-20260713133543
archive=/opt/stock-ts/.deploy_backups/research-data-depth-20260713133543/phase2-source-before.tgz
patch=/opt/stock-ts/.deploy_backups/research-data-depth-20260713133543/change.patch
```

The archive contains the pre-deployment source. Representative archive hashes:

```text
models.py=9e76fcc2b9c8720175a27dc8a8b21c45b7bcb660e301d5aac85c62cc1a38fb0a
stock_memo.py=f22c5ba915e37e98352060e8d85a4a1a572784d55e2a3d31fe8d479fe392a772
enrich_tdx_snapshot.py=5374cdab3e9777e5f58d4ec42a7695d6499598597837ac5d7fe4fa83df7d2dbd
```

Remote compile and import verification:

```text
Python 3.12.3
FundamentalPeriod MarketHistoryPoint ValuationPoint
phase2_import=ok
```

A temporary history-rich snapshot was served on port 18501 without modifying the production snapshot:

```text
preview_http=200
preview_bytes=297330
近 3 个交易日=4
财务 3 期=3
基于 20 个观察点=1
连续改善=3
data-market-stage="风险释放"
data-research-status="条件研究"
```

The preview process was then stopped and port 18501 was confirmed released.

Production service transition:

```text
before_pid=1609689
after_pid=1612349
service=active
started=Mon 2026-07-13 13:38:25 CST
direct_root=303
direct_login=200
```

Public-route verification:

```text
public_root=303
location=/login?next=%2F
public_login=200
public_login_bytes=107484
public_title=Jiewat Kaka FJ 研究分析平台
```

The root redirect is the expected authentication boundary. A first 15-second login download timed out after receiving 81,745 of 107,484 bytes; a second GET with a 45-second timeout completed with HTTP 200 and the expected title. The production snapshot remains unchanged and will accumulate bounded history through subsequent normal pipeline refreshes.
