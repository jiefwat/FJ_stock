# Final Review

Date: 2026-07-19
Scope: data resilience, deterministic analysis, Stock Lab interaction, persistence, and responsive delivery.

## Findings Resolved

1. **Partial provider failure could hide usable core data.** Sector and index acquisition are now isolated, normalized errors are exposed, and usable equity data continues to serve. Covered by backend API and provider tests.
2. **Missing opportunity evidence received a fake neutral score.** Missing factors are now omitted and available factor weights are renormalized. Covered by deterministic analysis tests.
3. **Stock Lab lacked the required trend surface.** It now renders an accessible responsive SVG from 180 real close bars with range and date context. Covered by a frontend interaction test and browser verification.
4. **Repeated watchlist adds surfaced as a failure.** Store creation is now idempotent by symbol, preserves the original thesis, and returns the existing item. Covered by a dedicated API regression test and browser verification.
5. **Data provenance labels did not reflect the resilient source mix.** Data Center and README now name Sina and Tencent explicitly, while iWenCai remains optional.
6. **Different strategy buttons returned generic or unsupported results.** Trend and oversold now apply distinct deterministic gates; capital and sector strategies stop with an explicit missing-data reason.
7. **Opportunity scores hid market-regime risk.** Candidate cards now separate base score, defensive/cautious penalty, final score, evidence coverage, and risk flags.
8. **Stock stance relied too heavily on one moving-average comparison.** The dossier now derives its stance from seven displayed factors and overlays close, MA5, MA20, and MA60.
9. **Watchlist creation and editing lacked a complete feedback loop.** Users can edit the thesis and invalidation before saving, receive a persistent confirmation, and continue editing from the research journal.
10. **Refresh metadata was ambiguous.** Data Center now separates market observation time from local fetch time and reports freshness, coverage, errors, and refresh completion.

## Final Assessment

No unresolved correctness or interaction finding blocks local release. All required modules load, the Today -> Market/Opportunities -> Stock Lab -> Watchlist path has no dead end, and desktop browser checks show no horizontal overflow.

The known sector-mapping, capital-flow, iWenCai, external-endpoint, and calendar limitations are documented in `test.md`; unavailable evidence is never presented as complete data or an investment recommendation.
