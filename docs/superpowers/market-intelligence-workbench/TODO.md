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
- [x] Add a Today opening desk so the daily route starts with market gate, priority review, and forbidden-action checks.

## Application Authentication Gate

- [x] Render a standalone login/register page before mounting the application shell.
- [x] Require a valid session for every market, analysis, refresh, and personal API.
- [x] Clear the application shell and query cache immediately on logout or session expiry.
- [x] Verify anonymous, authenticated, desktop, mobile, and production boundaries.

## Ask Stock Workbench

- [x] Resolve one A-share name or six-digit code from the full-market snapshot.
- [x] Reuse the deterministic Stock Lab dossier for risk, trend, valuation, action, and overview answers.
- [x] Add bounded optional Wencai semantic screening behind the provider layer.
- [x] Add an authenticated Ask Stock page without changing the existing page composition.
- [x] Preserve typed questions and render explicit validation and provider-unavailable states.
- [x] Pass `make verify` and complete production-build browser and API acceptance.
- [x] Convert Ask Stock into a multi-turn chat surface with previous-stock follow-up context.
- [x] Persist Ask Stock tab conversations, add follow-up prompts, retry failed turns, and accept unique short stock aliases.
- [x] Surface Ask Stock decision metrics and link semantic-screening stock codes back to Stock Lab.
- [x] Refactor Ask Stock into stock, holding-context, and portfolio-analysis answer paths without cross-account leakage.
- [x] Add portfolio concentration, sector concentration, target-drift, and risk-record diagnostics to Ask Stock.
- [x] Generate account-scoped Ask Stock rebalance plans with target drift, adjustment value, shares, and priority.
- [x] Carry single-stock Ask follow-up context for natural questions and hide provider branding from user-facing messages.
- [x] Separate market observation time from latest refresh time in user-facing timestamp labels.
- [x] Keep the refreshed timestamp chip and Today risk rail from causing document overflow at 390px.
- [x] Prevent weak two-character suffix aliases from making `青龙股份` look like multiple stocks.
- [x] Clarify Opportunities as research leads, not participation advice, with Stock Lab as the final participation gate.
- [x] Carry Opportunity source context into Stock Lab so lead review and final participation advice stay connected.
- [x] Add opportunity lead pre-judgement badges so users can see likely review risk before opening Stock Lab.
- [x] Move the top three Stock Lab advice reasons directly under the direct suggestion.
- [x] Add a Stock Lab evidence-audit gate so support, risk, gaps, and next review route are visible before deep evidence.
- [x] Add a Stock Lab opportunity-review outcome so leads explicitly upgrade, stay watch-only, or fail participation review.
- [x] Add Opportunity lead-layer filtering so users can focus on priority, watch-only, or high-risk leads.
- [x] Add an Opportunity queue gate so leads show review route, first dossier, and queue shortcuts before the candidate table.
- [x] Simplify Stock Lab by keeping the core decision cards visible and moving deep evidence into an expandable package.

## A-share Evidence And Market Intelligence

- [x] Freeze the pre-integration product as the remote annotated `v2` rollback tag.
- [x] Add strict source, document, theme, anomaly, and capability-state contracts.
- [x] Add CNINFO filings plus Eastmoney research metadata and instrument themes to Stock Lab.
- [x] Add sector-flow leaders and the latest available Dragon-Tiger observations to Market.
- [x] Add CLS as an independent fallback for market fast news.
- [x] Keep external evidence display-only and isolated from deterministic scores.
- [x] Expose source-specific ready, partial, empty, and unavailable states in Data Center.
- [x] Pass backend/frontend tests, production build, and live provider contract checks.
- [x] Complete authenticated local browser acceptance for Stock Lab, Market, Data Center, and 390px mobile width.
- [x] Make Stock Lab themes clickable into a Market theme dossier with related stocks.
- [x] Summarize theme constituent flows and make Market flow leaders open sector dossiers.
- [x] Turn Market sector and theme dossiers into compact constituent screeners with sort and range filters.
- [x] Add Market board-to-stock handoff reasons and preserve board context when opening Stock Lab.
- [x] Add Ask Stock source-context bridge from board/opportunity/stock workflows.
- [x] Add Ask Stock decision gates that mirror Stock Lab final advice and evidence ledger.
- [x] Add Ask Stock gate-aware deep links into Stock Lab review sections.
- [x] Add an Ask Stock post-answer review route that turns answers into Stock Lab checkpoints and follow-up questions.
- [x] Add a Stock Lab review route rail so long-form dossiers have an explicit reading order.
- [x] Add Market STOCK HANDOFF review-section routing into Stock Lab.
- [x] Add an actionable morning email brief preview with market, intelligence, candidates, holdings, and links.
