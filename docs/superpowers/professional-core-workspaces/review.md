# Review

Status: approved after one finding was fixed

## Scope

- Reviewed `main...codex/professional-core-workspaces` plus the final unstaged quality changes.
- Focused on stale/blocked behavior, cross-module risk authority, renderer escaping, one-verdict rules, account/write boundaries, and regression coverage.
- No model prompt, external AI call, credential, server configuration, or account-isolation code changed.

## Findings

### Resolved P2 - Opportunity gate could report `complete` while blocked

- Location: `src/stock_ts/research/opportunity_dossier.py`
- Cause: the gate displayed the upstream quote status even when unreliable candidate prices or a blocked market assessment had already stopped ranking.
- Risk: the page could show `数据暂停` and `data_status=complete` at the same time, weakening the audit trail.
- Fix: derive one effective evidence status; preserve upstream stale/blocked values and otherwise promote any effective stop to `blocked`.
- Regression: `tests/test_opportunity_dossier.py` covers both market-blocked and unreliable-pool cases.

## Open Questions / Assumptions

- `MarketRegimeAssessment` remains the only authority for the market risk budget.
- Real cash balance is still unavailable, so the portfolio page does not claim an actual account cash ratio.
- Candidate cards remain research inputs, not trade instructions or calibrated return forecasts.

## Residual Risks / Testing Gaps

- Five pre-existing daily-pipeline tests still fail because their fake runner does not create the newer required artifact; this branch does not modify that pipeline.
- The available real snapshot was stale, so browser smoke verified the hard-stop path with real data; fresh/active paths are covered by deterministic domain and renderer tests.
- No live broker, order execution, or external-provider mutation was performed.

## Decision

Approved for integration. No unresolved finding is attributable to this change set; deployment must preserve server data, secrets, reports, timers, Nginx, and the separate DSA service.
