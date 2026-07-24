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
