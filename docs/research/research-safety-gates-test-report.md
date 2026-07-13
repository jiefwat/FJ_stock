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

Status: deployed and verified on 2026-07-13.

### 8.1 Patch boundary and backup

- Target: `admin@47.82.145.207:/opt/stock-ts`
- Service: `stock-ts.service`
- Patch size: 18,791 bytes
- Patch scope: 5 Python source files, 216 insertions and 39 deletions
- `git apply --check`: passed before any remote write
- Backup directory: `/opt/stock-ts/.deploy_backups/research-safety-gates-20260713125430`
- Source archive: `/opt/stock-ts/.deploy_backups/research-safety-gates-20260713125430/src-stock-ts-before.tgz`
- Applied patch copy: `/opt/stock-ts/.deploy_backups/research-safety-gates-20260713125430/change.patch`

The five server files matched the `53fcd80` pre-change hashes before deployment. Their post-apply hashes match the locally verified source files.

### 8.2 Remote compile and behavior

The server uses Python 3.12.3. Explicit `py_compile` completed for all five files, and the remote behavior check returned:

```text
market=风险释放:10%-30%:58
stock=技术性观察:42
stale=数据暂停:0
remote_compile_import=ok
```

### 8.3 Temporary preview

The authenticated configuration first returned the expected 303 login redirect. A temporary read-only preview on `127.0.0.1:18501` with authentication disabled only for that preview process returned:

```text
preview_http=200
preview_bytes=305057
data-market-stage="数据暂停"
data-research-status="数据暂停"
stock_workspace=ok
market_workspace=ok
```

The preview process was stopped and port 18501 was confirmed released.

### 8.4 Production service and public route

`stock-ts.service` restarted successfully:

```text
before_pid=1604584
after_pid=1609689
service=active
started=Mon 2026-07-13 12:57:36 CST
```

Production authentication remains enabled:

```text
direct_root=303
direct_login=200
public_root=303
public_location=/login?next=%2F
public_login=200
public_login_title=Jiewat Kaka FJ 研究分析平台
```

The protected research content was verified through the temporary server preview rather than by bypassing production authentication.

### 8.5 Rollback verification

The backup archive lists all five expected paths and can stream their original content. Sample restored-content hashes match the pre-deploy baseline:

```text
evidence.py=828b2f08795d05529455a4e0a5a8d073b3849286de6deb2404c428cd0a08d751
web.py=abcd1241f4b1237d8fe79a37281f25966a73ff5c3a0bb15eaebc45ac41052b01
```

Rollback was not executed because every post-deploy check passed. If required, restore the five archived paths from `src-stock-ts-before.tgz` into `/opt/stock-ts` and restart `stock-ts.service`.
