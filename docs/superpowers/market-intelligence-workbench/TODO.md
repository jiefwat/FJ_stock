# TODO

- [x] Freeze product, interaction, data, and acceptance design.
- [x] Build normalized backend, analysis APIs, and local persistence.
- [x] Build six desktop workbench frontend modules.
- [x] Replace unreliable single-source full-market ingestion with Sina + Tencent multi-source acquisition.
- [x] Pass lint, types, unit tests, production build, and live-data gate.
- [x] Start locally and complete browser desktop workflow checks.
- [x] Complete review, merge, and handoff.

## Analyst Workflow V2

- [x] Expose market conclusions through a weighted evidence ledger.
- [x] Make strategy presets return distinct candidates or an explicit unavailable state.
- [x] Show base score, market-context penalty, evidence coverage, and missing factors.
- [x] Rebuild Stock Lab around MA5/20/60, reproducible factors, and balanced evidence.
- [x] Add editable thesis and invalidation fields before and after watchlist creation.
- [x] Distinguish observation time, fetch time, freshness, coverage, and refresh result.
- [x] Pass `make verify` and complete the production-build analyst workflow in a real browser.

## Market Events, Holdings, and Auto Refresh

- [x] Add market-event radar and readable event-to-sector verification.
- [x] Add richer opportunity diagnostics and candidate playbooks.
- [x] Add direct stock advice, comparison cards, and next actions.
- [x] Add local holdings CRUD with position analysis and rebalance hints.
- [x] Enable production auto refresh every 7,200 seconds.

## Delivery Efficiency

- [x] Keep the browser-facing market summary free of the unused full-equity universe.
- [x] Add a searchable, sortable, server-paginated full-market quote browser.
- [x] Add exchange filtering, selectable page size, and direct page navigation.
- [x] Add advanced full-market filters, URL-restorable state, and account-scoped saved views.
- [x] Make the Market shell and advanced filter workflow usable without document overflow at 390px.
- [x] Require authentication for holdings, watchlists, preferences, and saved views without default-owner fallback.

## Stock Analysis Engine V3

- [x] Extract EMA, MACD, ATR, Bollinger, and drawdown calculations into a pure indicator module.
- [x] Add visible momentum, volatility, price-extension, drawdown, and signal-confluence evidence.
- [x] Add descriptive 20-day rolling signal validation without feeding it back into the live score.
- [x] Make stop and trial-position guidance adapt to ATR while retaining structural support levels.
- [x] Keep anonymous stock research independent from private watchlist requests.
- [x] Preserve the desktop layout and remove Stock Lab horizontal overflow at 390px.

## Application Authentication Gate

- [x] Render a standalone login/register page before mounting the application shell.
- [x] Require a valid session for every market, analysis, refresh, and personal API.
- [x] Clear the application shell and query cache immediately on logout or session expiry.
- [ ] Verify anonymous, authenticated, desktop, mobile, and production boundaries.
