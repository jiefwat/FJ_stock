# Test Evidence

Status: verified locally on 2026-07-13

## Environment

- Branch: `codex/professional-core-workspaces`
- Base: `main@ac9ff6531b7159b78f5c80b4b9eb7c31796a9fc1`
- Primary test runtime: Python 3.11 virtual environment from the existing research worktree
- Compatibility runtime: Python 3.9

## Static Quality

```bash
make lint
git diff --check
python3 -m compileall -q src/stock_ts
```

Result: ruff passed, no whitespace errors, and Python compilation completed successfully.

## Focused Cross-Module Suite

```bash
PYTHONPATH=src <python> -m pytest -q \
  tests/test_market_regime.py \
  tests/test_opportunity_dossier.py \
  tests/test_portfolio_dossier.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_portfolio_interaction.py \
  tests/test_web_module_decisions.py \
  tests/test_web_layout.py \
  tests/test_web_professional_modules.py
```

Result: `135 passed in 1.51s`.

## Python 3.9 Contract Suite

The market, portfolio, opportunity domain and renderer tests passed under Python 3.9:

```text
30 passed in 0.28s
```

## Full Pytest

```text
5 failed, 537 passed, 11 warnings in 12.88s
```

No failure is introduced by this branch. The remaining five failures are the unchanged daily-pipeline baseline:

1. `test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
2. `test_daily_pipeline_continues_when_external_enrichment_times_out`
3. `test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
4. `test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
5. `test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`

The former sixth baseline failure for stale opportunity ranking now passes because stale candidates are explicitly downgraded to `待补数据` with zero eligible candidates.

## Local HTTP And Visual Smoke

- URL: `http://127.0.0.1:18653/?code=603278&provider=tdx-snapshot&holdings=data/portfolio/holdings.csv`
- HTTP: `200`, `310224` bytes.
- Real stale snapshot: one market verdict, one portfolio verdict, one opportunity gate, five market rail steps, five opportunity funnel steps, and 30 research candidates.
- Desktop `1440x1000`: no horizontal overflow; market rail uses five columns; portfolio uses one verdict, 11 queue items, 10 exposure rows, and 11 boundary cards.
- Mobile `390x844`: no horizontal overflow; market rail, portfolio grid, boundary grid, funnel, and candidate grid all collapse to one column.
- Final stale portfolio smoke confirmed `账本成本=true`, `累计盈亏指标=false`, and one primary portfolio verdict.

## Deployment Verification

- GitHub `origin/main`, local `main`, and server `main` all resolved to the code release commit `212b22684c3ce5ac0193fb392f183b980c47369e` before the deployment record commit.
- Server tracked worktree remained clean; only pre-existing ignored/untracked runtime assets were present.
- Server source contained all three primary-verdict markers, the five-step market rail, and stale portfolio ledger metrics.
- Server services: StockTs active, Signal Desk active, Nginx active; no post-restart traceback was found.
- Server-local `/healthz`: HTTP 200, body `ok`.
- Public `https://stock.jiewat-kaka-fj.com/healthz`: HTTP 200, body `ok`.
- Public root: HTTP 200 after the expected redirect to `https://stock.jiewat-kaka-fj.com/login?next=%2F`.
