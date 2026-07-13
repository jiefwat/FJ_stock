# Test Evidence

Status: accepted with five unchanged daily-pipeline baseline failures

Date: 2026-07-13

## Static Verification

```bash
make lint
/Users/fangjie/Documents/StockTs/.venv/bin/python -m compileall -q src/stock_ts
git diff --check
```

Result: Ruff reported `All checks passed!`; compileall and diff check exited `0`.

## Focused Web Regression

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_web_design_guide_shell.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_module_decisions.py \
  tests/test_web_compact_mode.py \
  tests/test_web_layout.py
```

Result: `120 passed in 2.06s`.

## Python 3.9 Contract Regression

```bash
PYTHONPATH=src /Users/fangjie/opt/anaconda3/bin/python3.9 -m pytest -q \
  tests/test_web_market_research_workspace.py \
  tests/test_web_design_guide_shell.py
```

Result: `19 passed in 0.22s` on Python `3.9.18`.

## Full Suite

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q
```

Result: `555 passed, 5 failed, 10 warnings in 18.13s`.

The five failures are the unchanged `tests/test_daily_pipeline.py` baseline failures:

- `test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
- `test_daily_pipeline_continues_when_external_enrichment_times_out`
- `test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
- `test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
- `test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`

This branch does not modify the daily-pipeline implementation or tests. No failure appeared outside that known baseline.

## Responsive Browser Smoke

Local preview: `http://127.0.0.1:18654`

Desktop `1440x1000`:

- document width `1425`, no page-level horizontal overflow;
- exactly one primary market verdict and three ordered phases;
- the session ruler uses three horizontal tracks;
- the intraday ledger is closed by default and retains the sector Top5 evidence;
- professional diagnosis and market action discipline both appear in close review.

Mobile `390x844`:

- document width `375`, no page-level horizontal overflow;
- the session ruler becomes one column and keeps all three phases;
- the intraday ledger is closed by default, then expands through native `details/summary`;
- expanded evidence retains strong Top5, weak Top5, movers, events, and three visible tables;
- the first evidence table uses a `245px` viewport with `536px` internal scroll width, so key columns remain readable without widening the page.

Visual inspection found and corrected one mobile readability defect: evidence tables previously compressed columns into single-character lines. A focused CSS contract was added before the fix, and the final browser smoke confirms internal scrolling instead of page overflow.

## Deployment Verification

Initial deployed commit: `692facd3e9088cbc0b5bcde62f399a82d0e4ddd2`

- Local `HEAD`, local `main`, local `origin/main`, live GitHub `main`, server `HEAD`, and server `refs/remotes/origin/main` all resolved to the initial deployed commit before this deployment record was added.
- Server `/opt/stock-ts` remained on branch `main` with zero tracked-file modifications.
- The release used a complete Git bundle and a server-side `--ff-only` merge; `.env`, `.secrets`, `data`, `reports`, Nginx, timers, Signal Desk, and DSA were not modified.
- Server compileall and imports for `stock_ts.web`, `stock_ts.webapp.market_workspace`, and `stock_ts.webapp.styles` exited `0` before restart.
- Only `stock-ts.service` was restarted. `stock-ts.service`, `stock-ts-signal-desk.service`, and `nginx` all reported `active` afterward.
- Server `http://127.0.0.1:8501/healthz` returned `ok`.
- Public `https://stock.jiewat-kaka-fj.com/healthz` returned HTTP `200` with body `ok`.
- Public root returned HTTP `303` to the existing login route, so public content inspection correctly stops at the authentication boundary; deployed source and health are verified separately.
