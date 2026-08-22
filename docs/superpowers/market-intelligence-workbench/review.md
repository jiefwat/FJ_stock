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
