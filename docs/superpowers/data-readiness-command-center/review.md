# Review

Status: accepted with known baseline failures

## Scope

Reviewed the complete branch diff against `main`, including the dossier model, recovery ordering, Web integration, source-ledger escaping, responsive CSS, regression tests, and requirement documentation.

## Findings

No unresolved P0-P2 findings remain.

One operational issue was found during visual review and fixed before acceptance:

- **Resolved:** full-chain validation was initially ranked before repairable data sources. Because it is a derived acceptance artifact rather than an upstream source, the page would have directed the user to a non-actionable first step. Recovery priority now restores market/K-line, candidate/fund-flow, news/event, announcement/fundamental inputs first and runs full-chain validation last. The corrected order has dedicated regression coverage.

## Assumptions

- Existing `DataCenterRow` status, freshness, missing-field, and impact calculations remain authoritative.
- Existing channel values are display-safe provider/file labels and never contain credentials. Future adapters must preserve that contract.
- The existing manual-refresh form remains the only mutation entry; this branch does not claim automatic repair success.

## Residual Risks And Testing Gaps

- The module-impact mapping is intentionally explicit. A future business module or data domain must update the mapping and tests or it will not appear in the impact matrix.
- Browser smoke used the current stale TDX snapshot, which exercises the highest-risk blocked state. Ready-state rendering is covered by unit and renderer tests rather than a second live provider fixture.
- Native disclosure behavior and expanded mobile layout were exercised, but there is no dedicated screen-reader audit beyond semantic table, `details/summary`, headings, and focus-visible CSS.

## Decision

Accept for fast-forward integration after the final evidence commit. The five full-suite failures remain the documented daily-pipeline baseline and are unrelated to this data-center presentation branch.
