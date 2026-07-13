# Test Evidence

Status: accepted with five unchanged daily-pipeline baseline failures

Date: 2026-07-13

## Static Verification

```bash
make lint
/Users/fangjie/Documents/StockTs/.venv/bin/python -m compileall -q src/stock_ts
git diff --check main
```

Result: all three commands exited `0`; Ruff reported `All checks passed!`.

## Focused Web Regression

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_web_design_guide_shell.py \
  tests/test_web_layout.py \
  tests/test_web_data_accuracy.py \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_module_decisions.py
```

Result: `128 passed in 2.11s`.

## Python 3.9 Contract Regression

```bash
PYTHONPATH=src /Users/fangjie/opt/anaconda3/bin/python3.9 -m pytest -q \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_market_research_workspace.py
```

Result: `16 passed in 0.26s` on Python `3.9.18`.

## Full Suite

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q
```

Result: `542 passed, 5 failed, 10 warnings in 17.51s`.

All five failures are the existing `tests/test_daily_pipeline.py` baseline failures:

- `test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
- `test_daily_pipeline_continues_when_external_enrichment_times_out`
- `test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
- `test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
- `test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`

This branch does not modify the daily pipeline or its tests. No new failure appeared outside that known baseline.

## Responsive Browser Smoke

Local preview: `http://127.0.0.1:18654`

Desktop `1440x1000`:

- document width `1425`, no horizontal overflow;
- Research Tape height `83px`, with all three secondary fields visible;
- opportunity front row `6`, overflow `24`, total candidate records `30`;
- opportunity overflow and source ledger default closed;
- opportunity risk register uses `position: sticky; top: 92px`;
- portfolio front queue `5` of `11`, overflow `6`;
- portfolio front boundaries `4` of `11`, overflow `7`;
- portfolio disclosures and supporting evidence default closed.

Mobile `390x844`:

- document width `375`, no horizontal overflow;
- stock search remains one row and navigation items are `112px` wide;
- only action gate, data state, trading date, and data-details route remain in the Research Tape;
- `每日大盘` begins at `537px`, inside the first viewport;
- opportunity front row remains `6`, overflow `24`, and the risk register returns to static flow.

Visual inspection confirmed the action gate is the global signature, module verdicts remain dominant, and disclosure controls do not visually compete with the research front row.

## Deployment Verification

Initial deployed commit: `7439f99c5ee3b53ce64fd73f91481efb87db5eaa`

- Local `main`, local `origin/main`, live GitHub `main`, server `HEAD`, and server `refs/remotes/origin/main` all resolved to the initial deployed commit before this deployment record was added.
- Server `/opt/stock-ts` remained on branch `main`; only the existing `.codex-backups/`, `.deploy_backups/`, `.env.bak.email-merge-20260711170050`, and `.secrets/` paths were untracked.
- Source backup: `/opt/stock-ts/.deploy_backups/20260713-201858-504fd08/source-504fd08.tar.gz`.
- Server compile and import checks exited `0` before restart.
- `stock-ts.service`, `stock-ts-signal-desk.service`, and `nginx` all reported `active` after restart.
- Server `http://127.0.0.1:8501/healthz` returned `ok`.
- Public `https://stock.jiewat-kaka-fj.com/healthz` returned HTTP `200` with body `ok`.
