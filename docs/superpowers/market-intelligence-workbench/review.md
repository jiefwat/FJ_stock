# Final Review

Date: 2026-07-19
Scope: data resilience, deterministic analysis, Stock Lab interaction, persistence, and desktop workbench delivery.

## Findings Resolved

1. **Partial provider failure could hide usable core data.** Sector and index acquisition are now isolated, normalized errors are exposed, and usable equity data continues to serve. Covered by backend API and provider tests.
2. **Missing opportunity evidence received a fake neutral score.** Missing factors are now omitted and available factor weights are renormalized. Covered by deterministic analysis tests.
3. **Stock Lab lacked the required trend surface.** It now renders an accessible desktop SVG from 180 real close bars with range and date context. Covered by a frontend interaction test and browser verification.
4. **Repeated watchlist adds surfaced as a failure.** Store creation is now idempotent by symbol, preserves the original thesis, and returns the existing item. Covered by a dedicated API regression test and browser verification.
5. **Data provenance labels did not reflect the resilient source mix.** Data Center and README now name Sina and Tencent explicitly, while semantic research enrichment remains optional.
6. **Different strategy buttons returned generic or unsupported results.** Trend and oversold now apply distinct deterministic gates; capital and sector strategies stop with an explicit missing-data reason.
7. **Opportunity scores hid market-regime risk.** Candidate cards now separate base score, defensive/cautious penalty, final score, evidence coverage, and risk flags.
8. **Stock stance relied too heavily on one moving-average comparison.** The dossier now derives its stance from seven displayed factors and overlays close, MA5, MA20, and MA60.
9. **Watchlist creation and editing lacked a complete feedback loop.** Users can edit the thesis and invalidation before saving, receive a persistent confirmation, and continue editing from the research journal.
10. **Refresh metadata was ambiguous.** Data Center now separates market observation time from local fetch time and reports freshness, coverage, errors, and refresh completion.

## Final Assessment

No unresolved correctness or interaction finding blocks local release. All required modules load, the Today -> Market/Opportunities -> Stock Lab -> Watchlist path has no dead end, and desktop browser checks show no horizontal overflow.

The known sector-mapping, capital-flow, semantic-research, external-endpoint, and calendar limitations are documented in `test.md`; unavailable evidence is never presented as complete data or an investment recommendation.

## 2026-07-23 Market Summary Payload Review

### Findings

No explicit findings. The change preserves the full `MarketSnapshot` inside the service, computes analysis from the complete equity universe, and projects only the browser-facing response into the compact contract.

### Open Questions And Assumptions

The repository frontend is the supported consumer of `/api/v1/market`; it already types and reads only metadata, indices, sectors, and analysis. No external client contract is documented in the repository.

### Residual Risks And Testing Gaps

An undocumented external client that reads `snapshot.equities` from this public v1 endpoint would need to migrate to the search, opportunity, or stock APIs. The response-contract regression test and production smoke check cover the supported browser workflow.

### Decision

Approved for deployment. No P0, P1, or P2 finding blocks release.

## 2026-07-24 Full-Market Browser Review

### Findings

No blocking findings. The new endpoint reads the existing cached snapshot, validates sort and pagination inputs, returns no more than 50 rows, and keeps missing numeric evidence after present values in both sort directions. The browser panel owns its own query state, so a quote-browser failure does not hide the market summary or sector analysis.

One presentation finding was resolved before release: a missing `change_pct` value inherited the positive color because it was compared as zero. A red-green regression now requires missing change evidence to remain visually neutral.

### Assumptions And Boundaries

- `/api/v1/market` remains the compact summary contract and does not return the full equity universe.
- `/api/v1/equities` is the supported browser contract for full-market inspection; provider access remains behind the service snapshot.
- Sorting is deterministic for the evidence available in a snapshot. No claim is made that unavailable turnover, amount, or market-cap fields equal zero.

### Residual Risks

The local in-app browser connection timed out despite healthy terminal and API checks, so the final interaction check must run against the deployed public origin. External market providers and their field coverage remain operational dependencies.

### Decision

Approved for production deployment after a fresh `make verify`. No P0, P1, or P2 finding remains open.

### Production Confirmation

The delegated deployment completed on release `20260724-114030-8d3fee6`. Independent API, persistence, service-state, and real-browser checks passed. The local browser-connection limitation did not reproduce on the public origin and no release-blocking finding remains.

## 2026-07-24 Full-Market Navigation Review

### Findings

No explicit P0, P1, or P2 findings. The new `exchange` input is a validated literal with a backward-compatible `all` default. Filtering stays in the service layer, precedes sorting and pagination, and never reaches provider code. Query cache identity includes exchange, page size, sort, direction, search, and page, preventing cross-filter result reuse.

During GREEN verification, a real interaction defect was resolved: native `max` validation prevented oversized page entries from reaching the component's clamp logic. The jump form now delegates validation to one deterministic path and a regression covers the behavior.

### Assumptions

The normalized production universe identifies listings with `SH.`, `SZ.`, and `BJ.` symbol prefixes. Unknown prefixes remain visible under `all` but do not leak into a named exchange filter.

### Residual Risks And Testing Gaps

Unit fixtures prove each contract branch, but the actual exchange partitions and 1,440-pixel control composition still require production API and real-browser checks after deployment. Existing third-party Starlette/httpx deprecation output remains unrelated to this change.

### Decision

Approved for deployment after a fresh repository gate. No high-priority finding blocks release.

### Production Confirmation

Release `20260724-120226-72e4c59` passed independent exchange-count, prefix, validation, page-size, persistence, service-state, and real-browser checks. The production universe contains all three supported exchange partitions and no release-blocking finding remains.

## 2026-08-16 Decision Intelligence Release Review

### Scope

Reviewed the complete pending release: decision-first analysis, recommendation history, financial/news intelligence, OpenAI-compatible question answering, account-scoped decision monitoring, morning email delivery, ten-minute cache warming, holding identity repair, frontend interaction changes, and public deployment configuration.

### Findings

No unresolved P0 or P1 finding blocks submission. Provider access remains isolated under `backend/src/marketdesk/providers/`; deterministic scoring remains under `analysis/`; browser code uses only `/api/v1/*`; account-scoped persistence and decision-event ownership are covered by regression tests. The committed configuration contains placeholders only, and the staged file set excludes `.env`, runtime databases, provider caches, Python caches, Playwright output, and `frontend/dist`.

### Open Questions And Assumptions

- The current public deployment remains a small-account workbench; the ten-minute decision monitor has not been load-tested for a large multi-tenant user base.
- SMTP delivery tests use a mocked transport. Production sender credentials, provider throttling, and mailbox deliverability remain operational concerns rather than code-contract guarantees.
- Public market, filing, research, news, Hong Kong, and US endpoints remain external dependencies whose field contracts can change.

### Residual Risks And Testing Gaps

- Real-provider financial-model calls were not exercised with a committed credential; timeout, parsing, fallback, and provider-style branches are covered with deterministic tests.
- Browser acceptance covered the deployed candidate workflow at desktop and 390 CSS pixels. Other pages are covered by component regressions and the production build but were not all replayed end to end in this final pass.
- FastAPI TestClient continues to emit the known third-party Starlette/httpx deprecation warning.

### Decision

Approved for commit and push. Full repository verification and public deployment acceptance passed, and no high-priority finding remains open.

## 2026-08-22 Ask Stock To Stock Lab Context Review

### Scope

Reviewed the pending Ask Stock and main-navigation changes in `frontend/src/features/ask/AskStockPage.tsx`, `frontend/src/app/App.tsx`, and `frontend/src/lib/recentResearch.ts`, plus the application-level regression fixture.

### Findings

No unresolved P0, P1, or P2 finding blocks release. The latest exact `symbol` and `name` returned by Ask Stock now replace stale recent research for navigation, including `llm_answer` responses from the financial-Skill path. The update remains account-scoped through the existing token-derived storage key, preserves known sector metadata, and removes its window event listener when the authenticated shell unmounts.

### Open Questions And Assumptions

- Only Ask Stock responses containing both a normalized symbol and name become the current stock. Portfolio and screening answers without one exact stock intentionally leave the previous stock unchanged.
- Direct navigation to `/stocks` remains an explicit empty-selection route; the main `个股` navigation item carries the latest exact research symbol when one exists.

### Residual Risks And Testing Gaps

- The local in-app browser session was logged out, so the authenticated click path was not replayed there without creating or using an account. The application-level test exercises the complete shell, Ask Stock response, stale-Moutai state, navigation click, and resulting hash route.
- Cross-tab synchronization still relies on the existing page-local research model; this fix guarantees same-tab page switching, which is the reported workflow.

### Decision

Approved for commit, push, and deployment after the final repository gate. No high-priority finding remains open.

## 2026-08-22 System Interaction Continuity Review

### Findings

No unresolved P0, P1, or P2 finding blocks release. Named financial-Skill answers now reuse the existing stock identity header and stock follow-ups instead of falling into the stockless compact presentation. The Decision Center's actionable section precedes controls in DOM and visual order. Global refresh success uses the already-returned snapshot metadata to communicate scope, completion, and data time.

### Assumptions And Boundaries

- Stockless `llm_answer` results intentionally keep the compact chat presentation and do not invent a stock route.
- Decision filters still control which actionable and monitoring events are visible; the change affects hierarchy, not filtering semantics.
- Refresh failure wording and the current workspace remain unchanged.

### Residual Risks And Testing Gaps

- The authenticated local browser is currently at the login gate, so component and application regressions are the acceptance path until an authorized user session is available.
- Refresh time is formatted in the browser's Chinese local time, matching the rest of the interface.

### Decision

Approved for the full repository gate and deployment. The changes remain frontend-only and preserve provider, deterministic-analysis, API, and account boundaries.

## 2026-08-22 Quant Market Structure Review

### Findings

No unresolved P0, P1, or P2 finding blocks release. Provider requests remain under `providers/`, market scoring and ladder/group derivation remain under `analysis/`, and every browser request stays under authenticated `/api/v1/*` routes. Strategy cards reuse the existing opportunity preset IDs instead of creating a second screening system.

The final review resolved four correctness issues before release: delayed raw bars can no longer become target-day streak evidence; zero-valued group flow no longer sorts as missing; missing quote fields no longer become zero-valued leader evidence or positive UI color; and N/C new listings no longer inherit ordinary board price-limit thresholds.

### Assumptions And Boundaries

- The ladder derives current limits from provider-normalized board/ST/name evidence. Historical ST transitions, exchange special-treatment dates beyond the visible name, and order-book sealed amount are unavailable and are not inferred.
- Concept and industry rankings are current cross-sections. Time-series rotation requires persisted historical group snapshots and is explicitly deferred.
- The service enriches the top 24 provider-ranked groups with constituents. Remaining catalog rows retain board-level change/flow evidence and lower evidence coverage rather than fabricated constituent statistics.

### Residual Risks And Testing Gaps

- Eastmoney group catalogs and constituents remain an external operational dependency. The service keeps an in-process last-good result and marks partial/stale evidence degraded, but does not yet persist group snapshots across a full service restart.
- The authenticated local browser remained at the login gate, so final visual and responsive acceptance is performed against the deployed same-origin session. Component tests cover all new interactions before deployment.
- FastAPI TestClient continues to emit the known third-party Starlette/httpx deprecation warning.

### Decision

Approved for commit, push, and public deployment after the fresh `make verify`: 235 backend tests, 91 frontend tests, production build, and the live-data gate passed.

### Production Confirmation

Release `20260822-230633-7a76d5a` is active at `https://stock.jiewat-kaka-fj.com`. Authenticated desktop and 390px acceptance covered Market, Opportunities, Limit Ladder, Concept Analysis, and Industry Analysis. All expected structure workflows rendered, the up/down ladder switch returned distinct live results, and every checked page avoided document overflow.

The first browser read used a StockTS tab that had remained open before deployment and therefore still ran the old in-memory SPA bundle. The server index and lazy market chunk already contained the new release; a normal reload loaded the new dashboard while preserving authentication. No StockTS-origin console error or warning remained. The only logged error came from an unrelated browser translation extension with an expired extension token.

The production release link, service, morning-email timer, health endpoint, and persistent database location were independently verified. No release-blocking finding remains.

## 2026-08-23 System Interface Redesign Review

### Scope

Reviewed the pending frontend-only redesign of the authenticated shell, navigation hierarchy, route context, loading/error states, responsive terminal theme, metadata, and collapse-state regression coverage.

### Findings

One interaction defect was resolved before release: the compact-rail CSS hid the same control required to expand the sidebar, which could leave desktop users trapped in compact mode. The expand control now remains visible in an intentionally taller compact brand area, while the automatically compact tablet rail continues to hide the manual toggle.

No unresolved P0, P1, or P2 finding remains. Navigation still reuses the existing routes and stock-context handoff, browser requests remain under `/api/v1/*`, and no provider, analysis, persistence, authentication, or financial-model boundary changed.

### Assumptions And Boundaries

- The sidebar's connection indicator is intentionally scoped to the Decision Change request and is labelled `提醒服务`; it does not claim that every market provider is healthy.
- Market-structure pages remain secondary entries on narrow screens and are reached from the Market shortcuts, preserving the seven-item mobile navigation limit.
- The visual redesign preserves red-up/green-down semantics and uses blue only for focus, selection, and primary interaction.

### Residual Risks And Testing Gaps

- Automated access to the local loopback page was blocked by the browser-control URL policy, so authenticated visual acceptance relies on the user's completed local test plus component/application regressions.
- CSS visibility itself is not computed by jsdom; the compact-rail regression verifies state, accessible naming, and persistence, while the resolved selector was reviewed directly.

### Decision

Approved for commit, push, and deployment from `codex/project-adjustments`. The user accepted the local version, the repository gate passed, and `main` remains unchanged for this release.

### Production Confirmation

Release `20260823-000818-34704ce` is active at `https://stock.jiewat-kaka-fj.com`. The public bundle fingerprints and redesign markers match the committed build, both systemd units are active, the health endpoint is normal, and persistent data remains outside the release. `main` was not modified.

## 2026-08-23 Interface Consistency Review

### Scope

Reviewed the authenticated routes as one product system, with emphasis on typography, surface hierarchy, control shape, status color, information density, and responsive continuity across Market, Opportunities, Stock Lab, Ask Stock, Holdings, Decision Change, Review, Limit Ladder, Concepts, and Industries.

### Findings

The review found a cross-generation visual conflict rather than a route-specific defect: the terminal shell used a cool gray/blue interaction language while several feature surfaces still used Songti display type, cream backgrounds, green editorial panels, pill-heavy controls, and unrelated radius/shadow scales. The consistency layer now centralizes UI/display/data typography, surface roles, control/panel radii, selection blue, tabular financial numbers, and shared dark decision headers. Warm colors remain only for caution; red-up/green-down semantics remain unchanged.

The Opportunities decision desk was also rebalanced so its decision, metrics, top candidate, and monitoring ownership remain readable without narrow vertical text. Stock Lab, Ask Stock, Holdings, Review, and market-structure surfaces now reuse the same header, panel, filter, form, badge, and state language while preserving all existing routes and behavior.

### Residual Risks And Testing Gaps

- The stylesheet still contains historical feature rules below the component layer; the new convergence layer intentionally overrides them without changing feature markup. A future component-by-component extraction can reduce CSS size without affecting this release.
- Authenticated visual acceptance remains user-led locally. Automated component coverage, production build validation, and public post-release checks cover behavior and delivery integrity.

### Decision

Approved for commit, push to `main`, and public deployment. The change is frontend-only, preserves provider and analysis boundaries, and passed the complete repository verification gate.

### Production Confirmation

Release `20260823-152204-0cdff06` is active at `https://stock.jiewat-kaka-fj.com`. The public index references the expected new JavaScript and CSS fingerprints, and the CSS contains the new typography, semantic-surface, selection, and opportunity-layout tokens. The public health endpoint is normal, both systemd units are active, and persistent data remains outside the release directory.

## 2026-08-23 Long-page Containment Review

### Scope

Reviewed the pending frontend-only containment pass for Limit Ladder, Concept Analysis, Industry Analysis, Recommendation Review, and Holdings, with emphasis on viewport use, progressive disclosure, responsive density, keyboard state, and preservation of existing analysis semantics.

### Findings

No unresolved P0, P1, or P2 finding blocks release. The Limit Ladder no longer constrains a large first-board result to one narrow column: each streak now spans the workbench, uses three stock columns on wide desktop, and initially renders twelve stocks. Concept and industry constituents, recommendation days, holdings, today's action queue, and the full ten-day holding plan now reveal additional detail only on request.

Expansion controls expose their current state with `aria-expanded`, retain visible focus treatment, reset after the relevant filter or selection changes, and always provide a reversible collapse action. Mobile uses two stock columns at common phone widths and falls back to one column below 360px. Existing confidence, unavailable-data, red-up/green-down, Stock Lab handoff, and `/api/v1/*` boundaries remain unchanged.

### Residual Risks And Testing Gaps

- The current account has only two recommendation-history days and no holdings, so live-browser pagination states for those two routes were validated through component fixtures containing seven days and larger holding sets.
- Very large expanded result sets intentionally restore document scrolling; expansion is an explicit user action and can be reversed without changing filters.
- The stylesheet still includes historical layers. This pass adds a final containment layer instead of restructuring unrelated feature CSS.

### Decision

Approved for commit, push to `main`, and public deployment. The final repository gate passed with 235 backend tests, 95 frontend tests, the production build, and live-data quality checks. Authenticated browser acceptance found no origin-owned console errors or document-level horizontal overflow at 1440px or 390px.

### Production Confirmation

Release `20260823-155528-ec90856` is active at `https://stock.jiewat-kaka-fj.com`. The public index references the expected JavaScript and CSS fingerprints, the deployed CSS contains the long-page containment rules, both systemd units are active, and persistent data remains outside the release. Authenticated public-browser acceptance reproduced the desktop three-column and mobile two-column ladder layouts without horizontal overflow or console errors.

## 2026-08-23 Core Task-flow Interaction Review

### Scope

Reviewed the authenticated workflow through direct desktop and 390px browser operation, concentrating on the first useful action, page dead ends, duplicate inputs, state feedback, and narrow-screen control sizing across Opportunities, Holdings, Decision Change, Stock Lab, and Ask Stock.

### Findings

No unresolved P0, P1, or P2 finding blocks release. Opportunities now presents the current decision before strategy explanation, reduces nine oversized strategy cards to one horizontal switcher plus a single active summary, announces strategy updates, and labels each candidate row with a reversible `查看判断` / `收起判断` action. The mobile strategy treatment progressively removes its decorative header while retaining entry, exit, confidence, and current-best evidence.

Empty Holdings now starts with a directly visible registration workflow and explicitly states that only real positions produce rebalance reminders; zero-value portfolio charts and meaningless sorting controls no longer appear. Empty Decision Change provides routes into today's candidates, real holdings, and the market overview. Stock Lab and Ask Stock no longer compete with a second global research input, while a new Stock Lab user receives neutral workflow routes without defaulting to Moutai or any other stock.

### Human-factors Notes

- Decision and next action precede explanation on the highest-frequency candidate route.
- Empty states preserve user agency instead of ending the workflow.
- Strategy choice uses persistent pressed state and a polite live-region update without moving scroll position.
- Narrow-screen holding fields now measure 162px for paired inputs and 336px for narrative inputs instead of the previous 55px compressed controls.
- Reduced-motion preferences disable the only new status animation.

### Decision

Approved for push to `main` and public deployment. The change is frontend-only, preserves all provider, deterministic-analysis, authenticated API, and account boundaries, and passed the complete repository gate.

### Production Confirmation

Release `20260823-161624-c394042` is active at `https://stock.jiewat-kaka-fj.com`. The deployed index references `index-Ccp3p6Mr.js` and `index-Dbr3osb9.css`; authenticated production acceptance confirmed the decision-first candidate order, strategy switch state, empty-holding onboarding, empty-reminder routes, and single-input Stock Lab behavior at desktop and 390px. No StockTS-origin console error, warning, or horizontal document overflow remained.

The health endpoint is normal, `stock-ts.service` and `stock-ts-morning-email.timer` are active, the release contains no runtime data directory, and the persistent database remains under `/opt/aster-market/data`.

## 2026-08-23 Full-site Task-path Review

### Scope

Reviewed all ten authenticated routes as one interaction system: Decision Change, Market, Opportunities, Recommendation Review, Stock Lab, Ask Stock, Holdings, Limit Ladder, Concept Analysis, and Industry Analysis. The review covered route identity, first-screen intent, long-page orientation, filter-to-result feedback, mobile route reachability, and responsive overflow.

### Findings

The earlier optimization improved several core workflows but left route-level composition inconsistent. The full-site pass now gives every route one compact workbench header and an explicit, keyboard-operable task path. Each path reflects the domain rather than repeating generic tabs: Market moves from today's decision to structure and deep scan; Review moves from strategy to performance and ledger; Stock Lab moves from stock identity to conclusion, questions, and evidence; the structure routes move from scope to strength and constituents.

Ask Stock now exposes its current conversation object before the thread so follow-ups are less likely to drift to a stale stock. Holdings exposes the real-position boundary in every loading, error, empty, and populated state. Concept and Industry repair the selected URL state when filtering removes the current group. The narrow group catalog no longer compresses its title vertically.

The mobile shell no longer hides the three market-structure routes. All ten destinations share one horizontally scrollable bottom navigation, and route changes center the active destination automatically. Red-up/green-down meaning, confidence wording, account boundaries, provider isolation, deterministic analysis, and `/api/v1/*` browser access remain unchanged.

### Decision

Approved for commit, push to `main`, and public deployment. No unresolved P0, P1, or P2 finding remains. The complete repository gate and authenticated desktop/mobile route matrix passed before release.

### Production Confirmation

Release `20260823-163858-c466036` is active at `https://stock.jiewat-kaka-fj.com`. Authenticated public acceptance covered all ten routes at desktop and mobile sizes. Every task path responded, every mobile destination remained reachable and centered when active, all checked pages had zero document overflow, and the browser reported no StockTS-origin error or warning.

The public index references the expected `index-BsqmYdgM.js` and `index-Bptze3q3.css` assets. `/healthz`, `stock-ts.service`, and `stock-ts-morning-email.timer` are normal; release-local runtime data is absent and the persistent database remains outside the release.

## 2026-08-23 Market-group Detail Evidence Review

### Scope

Reviewed the Concept Analysis screenshot where `5G概念` had valid board-level change and capital flow but showed `N/A` for breadth and turnover, no leader or constituents, and a large uninformative remainder in the focus panel.

### Confirmed Cause And Fix

The catalog intentionally prefetches constituents for only the first 24 provider-ranked groups, while deterministic heat sorting can move any of the full 100 groups into the visible selection. A group outside the prefetch window therefore looked like a complete result even though only its board quote was present.

The catalog remains bounded, but the selected concept or industry now uses a dedicated authenticated `/api/v1/market-structure/groups/{kind}/{group_code}` detail route. The service validates the code against the current catalog, reuses already-hydrated evidence, otherwise fetches the selected constituents, reruns the deterministic group analysis, and caches only successful non-empty detail results for ten minutes. Empty or failed requests remain retryable instead of being preserved as a false complete state.

The focus panel now names the loading operation, keeps board-level metrics visible, and replaces the empty constituent area with a compact explanation and inline retry when member evidence remains unavailable. Missing breadth, turnover, and leader values remain `N/A`; confidence remains evidence coverage rather than an upside probability.

### Verification And Residual Risk

- Focused regressions cover a 25th catalog group, invalid codes, an initially empty provider response followed by a successful retry, hydrated leader/constituent rendering, and the compact failure action.
- The live provider returned 80 constituents for `BK0714` (`5G概念`), confirming the production defect was hydration scope rather than an absent upstream catalog.
- The complete repository gate passed with 237 backend tests, 99 frontend tests, production build, and the live-data quality check.
- Automated local loopback navigation was blocked by the browser-control URL policy; public authenticated desktop and 390px acceptance remains required after deployment.

### Decision

Approved for commit, push to `main`, and public deployment. Provider access remains inside the backend provider/service boundary, deterministic ranking remains under `analysis/`, and browser code uses only `/api/v1/*`.

### Production Confirmation

Release `20260823-191134-e22c82b` is active at `https://stock.jiewat-kaka-fj.com`. The public index references the expected JavaScript and CSS fingerprints, and the deployed lazy group chunk contains the selected-detail API path, compact `成分股证据暂未取得` state, and synchronized `只成分` catalog status. The new detail path returns the authenticated JSON boundary instead of falling through to the SPA.

The public health endpoint is normal, `stock-ts.service` and `stock-ts-morning-email.timer` are active, release-local runtime data is absent, and the persistent database remains outside the release. Browser visual acceptance could not be completed because the local browser tab became trapped on a browser-managed blocked error URL; component tests cover desktop/mobile markup and the public delivery contract is independently verified.

## 2026-08-23 Market-group Prewarm Review

### Scope

Reviewed the visible loading spinner when opening Concept Analysis or Industry Analysis, including the real provider latency, scheduled refresh order, service cache behavior, and selected-detail transition.

### Confirmed Cause And Fix

Live measurement showed that a cold market refresh took 4.657 seconds in the background, while concept and industry catalog requests took about 0.11–0.16 seconds and a selected detail request took about 0.016 seconds. The most noticeable defect was therefore perceptual: React exposed the loading panel immediately, making even a fast cacheable request flash as a spinner. The scheduled ten-minute refresh also warmed market, stock, and strategy data but did not explicitly warm the group-detail cache.

The scheduled refresh now loads both catalogs and the twelve highest-ranked groups from each kind before stock and strategy monitoring. Detail hydration is bounded to six concurrent requests, reuses the existing ten-minute cache, counts only non-empty constituent evidence as ready, and isolates provider failures so the rest of the refresh continues. Empty results remain uncached and retryable.

The group focus keeps board-level evidence visible and waits 240 milliseconds before exposing the detailed loading state. Fast cached responses therefore settle without a loading flash; genuinely slow requests still name the work in progress, and failed or empty detail responses still expose the existing truthful retry state.

### Decision

Approved for commit, push to `main`, and public deployment. Provider access remains behind the service/provider boundary, deterministic analysis remains under `analysis/`, and the browser continues to use only `/api/v1/*`.
