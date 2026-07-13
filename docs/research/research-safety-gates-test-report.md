# Research Safety Gates Test Report

**Date:** 2026-07-13  
**Branch:** `codex/research-safety-gates`  
**Source commit tested:** `d6a17ca`  
**Scope:** Phase 1 research safety gates

## 1. Result

The Phase 1 changes pass the focused research regression set and the full ruff check. The full pytest suite has the same six failures as the pre-change baseline and no new failures.

| Check | Before | After | Result |
| --- | ---: | ---: | --- |
| Focused research/Web tests | 17 passed | 32 passed | Pass |
| Full pytest | 463 passed, 6 failed, 11 warnings | 478 passed, 6 failed, 11 warnings | No new failures |
| Full ruff | Not re-recorded in isolated baseline | All checks passed | Pass |
| Local HTTP GET | Not applicable | 200, 310442 bytes | Pass |

The increase from 463 to 478 passing tests is due to the 15 new safety-gate tests.

## 2. Environment

- Worktree: `/Users/fangjie/.config/superpowers/worktrees/StockTs/codex-research-safety-gates`
- Python: 3.11.15
- pytest: 9.1.1
- ruff: 0.15.16
- Local ignored runtime data is linked from the primary checkout for comparable Web and full-suite verification. No local holdings, snapshots, reports, or credentials are committed.

The primary checkout's old `.venv` resolves to Python 3.9.18, which cannot import `enum.StrEnum`. Verification therefore uses a dedicated ignored Python 3.11 environment in the isolated worktree. `pyproject.toml` still declares Python `>=3.9`; that metadata mismatch is recorded for the deployment-governance phase rather than changed in this safety patch.

## 3. Focused Regression Evidence

Command:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_research_evidence.py \
  tests/test_market_regime.py \
  tests/test_stock_research_memo.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_stock_research_workspace.py \
  tests/test_web_data_accuracy.py::test_data_quality_exposes_typed_research_quote_status
```

Result:

```text
32 passed in 0.12s
```

Covered behavior:

- extreme limit-down risk overrides rotation;
- contradictory high-heat/high-risk inputs reduce confidence;
- stale or blocked stock quotes produce `数据暂停` with confidence 0;
- metadata-only fundamentals have zero metric coverage;
- invalid valuation references do not count as comparable evidence;
- blank event titles do not count as event evidence;
- complete valid inputs retain `条件研究`;
- market and stock Web orchestration consume typed quote status.

## 4. Original Symptom Reproduction

The post-change reproduction script returned:

```text
market=风险释放 budget=10%-30% confidence=58
stock=技术性观察 confidence=42 fundamentals=missing events=missing
stale_stock=数据暂停 confidence=0
```

The same script before implementation returned:

```text
market=轮动 budget=50%-70% confidence=70
stock=条件研究 confidence=78 fundamentals=degraded events=degraded
```

## 5. Lint

Command:

```bash
/Users/fangjie/Documents/StockTs/.venv/bin/ruff check src tests
```

Result:

```text
All checks passed!
```

The ruff executable is a standalone binary; it is not affected by the primary checkout's Python 3.9 interpreter link.

## 6. Full Suite

Command:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Result:

```text
6 failed, 478 passed, 11 warnings in 12.82s
```

The six failures are unchanged from the baseline:

1. `tests/test_daily_pipeline.py::test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
2. `tests/test_daily_pipeline.py::test_daily_pipeline_continues_when_external_enrichment_times_out`
3. `tests/test_daily_pipeline.py::test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
4. `tests/test_daily_pipeline.py::test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
5. `tests/test_daily_pipeline.py::test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`
6. `tests/test_web_data_accuracy.py::test_web_blocks_opportunity_ranking_when_snapshot_trade_date_is_stale`

The first five are pre-existing daily-pipeline result failures. The sixth expects an older candidate-quality sentence that the current UI no longer renders. The updated end-to-end case reaches that old assertion only after successfully proving `data-research-status="数据暂停"` for the stale stock memo.

## 7. Local HTTP Smoke

Start command:

```bash
HOST=127.0.0.1 PORT=18502 PYTHONPATH=src .venv/bin/python -m stock_ts.web
```

GET result for `/?code=603278&provider=tdx-snapshot&holdings=data/portfolio/holdings.csv`:

```text
http_status=200
response_bytes=310442
data-market-stage="数据暂停"
data-research-status="数据暂停"
```

Both research workspaces pause because the current linked local snapshot and pipeline artifact are stale relative to 2026-07-13. This confirms the hard gate on the real Web orchestration path. The temporary server was stopped after the check.

## 8. Deployment Verification

Status: pending incremental deployment.

The deployment record must add:

- server patch-check result;
- exact source backup path;
- explicit remote compile/import result;
- temporary port 18501 preview GET result;
- `stock-ts.service` active state after restart;
- public `https://stock.jiewat-kaka-fj.com/` GET status and research-workspace markers;
- rollback source path and whether rollback was exercised.
