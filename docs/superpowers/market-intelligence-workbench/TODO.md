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
- [x] Enable production auto refresh every 600 seconds so market and recommendation caches stay warm.

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
- [x] Add historical K-line confirmation to Opportunity candidates so lead ranking checks trend, extension, volatility, drawdown, and volume before Stock Lab review.
- [x] Collapse Opportunity candidates into a compact stock list and expand details only after the user clicks a stock.
- [x] Simplify Stock Lab by keeping the core decision cards visible and moving deep evidence into an expandable package.
- [x] Add an OpenAI-compatible financial-model mode with bounded deterministic context and automatic local-analysis fallback.

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
- [x] Make Ask Stock answer conclusion-first and move Stock Lab gate details behind an explicit evidence expansion.
- [x] Keep Ask Stock conclusion text concise and answer target-price questions without replaying the full Stock Lab dossier.
- [x] Add Ask Stock movement intent so recent big-rise/big-drop questions answer the price-move cause instead of generic participation advice.
- [x] Add an Ask Stock answer playbook and route basic-fundamental/catalyst questions before generic overview/action templates.
- [x] Expose the Ask Stock answer playbook as scene-route prompt cards so users can choose movement, fundamental, catalyst, risk, action, or portfolio questions directly.
- [x] Add a Stock Lab review route rail so long-form dossiers have an explicit reading order.
- [x] Add Market STOCK HANDOFF review-section routing into Stock Lab.
- [x] Add an actionable morning email brief preview with market, intelligence, candidates, holdings, and links.
- [x] Add a Market execution console so broad-market review starts with breadth, capital line, risk brake, and next instruction.
- [x] Reorder Market page structure so board/theme dossiers stay next to sector heat and the full-market browser moves to deep-scan position.

## Recommendation Performance Ledger

- [x] Freeze each strategy's top three daily candidates without overwriting selection-time prices, ranks, scores, or evidence coverage.
- [x] Rank candidates with strategy-specific signals and version new snapshots without rewriting legacy recommendation history.
- [x] Precompute every recommendation-review strategy during scheduled refresh and prefetch a ledger only when the user points to or focuses that strategy.
- [x] Append daily market observations and calculate deterministic T+1, T+5, T+20, current, peak, drawdown, and benchmark-relative returns.
- [x] Keep immature samples out of the formal 20-session hit rate and state the non-retroactive tracking boundary explicitly.
- [x] Add an authenticated Recommendation Review page with strategy switching, daily ledgers, stock handoff links, and responsive mobile navigation.
- [x] Capture the trend strategy during scheduled refresh while keeping all browser access under `/api/v1/*`.
- [x] Precompute all nine visible opportunity strategies every ten minutes, serve warmed results, and present research follow-ups as system-owned monitoring instead of user chores.

## Decision-first Experience

- [x] Lead Market, Opportunities, Stock Lab, Ask Stock, and Holdings with a direct action instead of requiring the user to interpret technical evidence.
- [x] Use one plain-language action vocabulary across candidate and holding decisions while keeping evidence optional.
- [x] Reuse background-monitored K-line history in Stock Lab and return a safe no-participation decision when the live K-line source is unavailable.
- [x] Reduce expanded Opportunity details to decision, reason, risk, and change condition while keeping system monitoring visible and professional evidence collapsed.
- [x] Unify the workbench around neutral surfaces, one blue interaction accent, compact route controls, and semantic-only market colors across desktop and mobile.
- [x] Keep page-path observers stable across data rerenders and preserve the selected step while collapsed sections open and reflow.
- [x] Browser-verify Decisions, Market, Opportunities, Stock Lab, Ask Stock, and Holdings at desktop and 390px with no application console errors or horizontal overflow.

## Decision Change Center

- [x] Persist account-scoped candidate and holding decision snapshots and material action-change events.
- [x] Establish a silent first-run baseline, suppress score/ranking noise, and deduplicate repeated observations.
- [x] Queue email only for holding trim or exit decisions and isolate bounded delivery failures from market refresh.
- [x] Add an authenticated decision center with action/monitoring separation, unread state, and direct research links.
- [x] Keep the seven-entry navigation and decision cards usable without horizontal overflow at 390px.

## Stock Financial And News Intelligence

- [x] Add normalized multi-period financial statements and stock-specific news behind the provider boundary.
- [x] Score financial health conservatively and let only recent explicit hard-risk news reduce the stock score.
- [x] Keep financial and news failures independent from each other and from the core stock dossier.
- [x] Show concise financial-health and 30-day sentiment cards with expandable cited details.
- [x] Cache normalized stock intelligence and prewarm tracked/default stocks during the ten-minute server refresh.
- [x] Detect multi-period revenue and profit slowdowns instead of judging only the latest report.
- [x] Deduplicate syndicated copies of the same news event before counting risk or sentiment.
- [x] Merge company, news, price, and invalidation into one first-screen decision view.
- [x] Load company evidence only when professional details are opened and keep the stock result fresh for the ten-minute server window.
- [x] Warm default, holding, and watchlist stocks before the heavier strategy refresh so service restarts do not leave the main stock page cold.
- [x] Exclude broad-market news roundups when the selected stock is only mentioned incidentally in the article summary.
- [x] Replace the empty historical-chart column with a compact, explicit risk-discipline state on desktop and mobile.
- [x] Make Stock Lab task routes open their target, keep secondary panels mutually exclusive, and support keyboard stock selection.

## Stock Participation Gate V4

- [x] Normalize stock evidence weights to exactly 100% so missing research or news cannot be hidden by score clamping.
- [x] Make recent explicit hard-risk news block new participation and return the concrete blocker through the stock advice contract.
- [x] Render the server-owned blocker before position discipline and remove browser-side participation recomputation.
- [x] Collapse secondary decision drivers and Ask Stock shortcuts behind explicit, responsive disclosures.
- [x] Verify the blocker-first flow, disclosure interaction, contrast, and zero horizontal overflow at desktop and 390px.
- [x] Pass the full `make verify` gate after the Stock Participation Gate V4 changes.

## Stock Lab Information Architecture V5

- [x] Replace the stock-page path with four short decision sections: conclusion, evidence, follow-up, and details.
- [x] Reduce the first screen to stock identity, one primary action, blocker or position discipline, and one reason and risk.
- [x] Move the price chart and participation, stop, and realization conditions behind explicit disclosures.
- [x] Keep evidence, follow-up, and professional details mutually exclusive and group deep data into three secondary directories.
- [x] Render the mobile stock directory as a complete two-by-two grid instead of a horizontally clipped rail.
- [x] Pass the full `make verify` gate after the Stock Lab Information Architecture V5 changes.

## Stock Lab Interaction Polish V6

- [x] Remove the duplicate selected-stock status card and shorten the selected-state page description.
- [x] Collapse stock search behind a compact switcher after selection while keeping the empty state search immediate.
- [x] Focus and select the switcher input on open, and let Escape close it without changing the current stock.
- [x] Fit all four stock sections on one mobile row at normal phone widths with a two-row fallback for very narrow screens.
- [x] Add short, directional disclosure transitions while respecting reduced-motion preferences.
- [x] Pass the full `make verify` gate after the Stock Lab Interaction Polish V6 changes.

## Stock Lab Editorial UI V7

- [x] Replace the boxed stock-page path with a quiet ruled navigation and typographic active state.
- [x] Remove the main stock card, shadow, dark verdict block, metric pills, and large neutral fills.
- [x] Preserve semantic red only for blocked participation and explicit risk evidence.
- [x] Group the decision summary with shared edges, whitespace, and restrained hairlines instead of nested surfaces.
- [x] Flatten the evidence directory, question routes, deep groups, score rows, and technical details into an editorial reading flow.
- [x] Pass the full `make verify` gate after the Stock Lab Editorial UI V7 changes.
- [x] Deploy the verified editorial Stock Lab release and confirm public assets, services, authentication, and persistent-data isolation.

## Stock Lab Progressive Disclosure V8

- [x] Reduce the loaded-stock first layer to identity, verdict, blocker, evidence quality, and position discipline.
- [x] Remove the duplicated why/risk/trend strip and desktop/mobile Ask action groups.
- [x] Keep the sector destination as quiet identity metadata and keep Ask entry in the dedicated question directory.
- [x] Move price history into the evidence disclosure while preserving the unavailable-history fallback.
- [x] Remove the second visible directory heading and keep `PageTaskRail` as the single page path.
- [x] Preserve mutually exclusive evidence, question, and professional-detail disclosures with deep-link behavior.
- [x] Pass focused Stock Lab/header tests, frontend types, `git diff --check`, and the full `make verify` gate.
- [x] Deploy release `20260829-212240-e868aff-dirty` and verify public assets, authentication, services, timer, and persistent-data isolation.

## Reminder Confidence And Human Factors

- [x] Keep decision-event reads compatible with persistent databases created by newer application versions.
- [x] Add reminder category and read-state filters, progressive disclosure, evidence confidence, and inline retry.
- [x] Suppress holding actions after the account no longer owns the referenced holding and remove its active snapshot on deletion.
- [x] Separate immature process returns from formal T+20 results and show positive, negative, flat, and immature distributions.
- [x] Start Stock Lab from an explicit stock choice, remove the default Moutai assumption, and explain that confidence is not upside probability.
- [x] Expose Ask Stock as a backend-only financial-analysis Skill contract with local evidence, confidence, and no-holding language safeguards.
- [x] Carry the latest Ask Stock symbol into Stock Lab navigation, including financial-Skill answers, without letting stale Moutai history override it.
- [x] Keep stock identity, intent, evidence time, confidence, and follow-up routes visible on named financial-Skill answers.
- [x] Put actionable decision changes before reminder filters while keeping system monitoring last.
- [x] Make global refresh confirmation state its all-site scope and the resulting refresh time.
- [x] Keep named morning-email stocks scoped to current holdings, label market candidates as non-holding research, and cancel queued alerts after a holding is removed.
- [x] Keep personalized morning briefs and decision alerts bound to the owning account, ignoring global receiver overrides and reserved test accounts.

## Plain Unified Workbench

- [x] Replace route-specific card, radius, and shadow systems with one square, flat section treatment.
- [x] Keep tinted backgrounds only for decisions, real risk, warnings, and degraded-data states.
- [x] Flatten nested metric cards into ruled rows and cells while preserving financial number alignment.
- [x] Unify page title scale, task-path navigation, controls, empty states, and disclosure treatment.
- [x] Consolidate the Opportunities decision area into one continuous hierarchy.
- [x] Remove decorative Market breadth bars and neutralize unselected Concept and Industry evidence bars.
- [x] Verify all ten desktop routes and key 390px workflows without document-level horizontal overflow.
- [x] Pass the complete `make verify` repository gate for the unified workbench.
- [x] Deploy release `20260904-125205-e868aff-dirty` and verify public assets, all ten authenticated routes, services, account boundaries, and persistent-data isolation.

## Quant Market Structure

- [x] Rebuild the Market overview around one explicit snapshot, breadth distribution, liquidity, capital participation, limit counts, sector extremes, and active stocks.
- [x] Make Opportunities use a stable strategy registry shared with the existing candidate workflow and recommendation history.
- [x] Add exchange-aware up/down limit ladders verified only with target-date, unadjusted daily prices.
- [x] Add separate concept and industry catalogs with search, sorting, group focus, leaders, constituents, confidence, and Stock Lab handoff.
- [x] Keep sealed-order amount and unsupported rotation history explicitly unavailable instead of estimating them.
- [x] Retain the last valid group cross-section on catalog failure and label stale or partial evidence as degraded.
- [x] Preserve N/A semantics, red-up/green-down presentation, desktop density, and narrow-screen usability.
- [x] Commit, push, deploy, and independently verify the public market-structure release.
- [x] Prewarm popular concept and industry evidence during scheduled refresh and suppress imperceptibly short loading flashes.
