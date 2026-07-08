# StockTS UI Simplification Design

## Goal

Make the StockTS web app feel faster and easier to use by removing repeated header content, giving each module one clear job, and moving secondary details behind progressive disclosure. The change is local-first and must not be deployed until the user approves the local result.

## Current Issues

- The page repeats module context in the sidebar and the top hero, so the first screen feels busy.
- The top of the app has multiple competing rows: brand hero, status cards, stock switcher, global summary, and module heading.
- Module pages expose many supporting details at once, making the primary decision hard to find.
- Smooth scrolling, large shadows, repeated panels, and all workspace content in the DOM contribute to a slow-feeling interface.

## Chosen Direction

Use a compact research-console layout:

- Keep the left navigation as the main module switcher.
- Replace the large top hero with a single compact command bar containing current module, stock code, provider, and session status.
- Keep one global summary strip, but make it shorter and action-oriented.
- Make each module start with a clear focus line: what the user should decide on that page.
- Put secondary data quality, long tables, and explanatory material into existing `details.detail-shell` patterns where possible.
- Reduce visual weight: smaller cards, fewer shadows, no smooth scrolling by default, less repeated module description.

## Module Focus

- A股大盘: decide whether today is attack, balance, or defense.
- 板块分析: identify mainline sectors, rotation speed, and persistence.
- 涨停板: read short-term sentiment and strongest directions.
- 跌停板: identify risk pockets and avoid fading areas.
- 智能选股: rank candidates, filter risk, and jump to stock analysis.
- 个股分析: read conclusion, triggers, invalidation, and risk boundary.
- 持仓分析: check concentration, cost, risk, and adjustment plan.
- 每日复盘报告: review final shareable daily text.
- 消息渠道: test and configure outbound channels without exposing secrets.

## Files

- `src/stock_ts/webapp/shell.py`: simplify sidebar, topbar, toolbar, workspace script.
- `src/stock_ts/webapp/styles.py`: compact layout, reduce animation/shadow, improve responsive behavior.
- `src/stock_ts/web.py`: reduce global summary density and wrap secondary module content where safe.
- Tests under `tests/`: add lightweight rendering checks if existing tests support Web output.

## Testing

- Run `make lint` if available.
- Run `make test` if available.
- Start local app with `HOST=127.0.0.1 PORT=8501 STOCK_TS_PUBLIC_READONLY=1 PYTHONPATH=src python3 -m stock_ts.web`.
- Open `http://127.0.0.1:8501/?provider=auto&holdings=data%2Fportfolio%2Fholdings.csv&code=002487#workspace-smart-select` and verify the first screen is simpler.
- Click all workspace links and confirm module switching still works.

## Deployment Gate

No server deployment occurs in this work. Deployment to Aliyun only happens after the user confirms the local result.
