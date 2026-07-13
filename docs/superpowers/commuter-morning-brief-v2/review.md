# Review

Status: accepted

Date: 2026-07-13

## Scope

Reviewed the branch against `main`, focusing on morning-report composition, stale-data ordering, personalized holdings, candidate limits, delivery side effects, and test coverage.

## Findings

No explicit correctness, safety, or architecture findings remain.

During implementation, review caught one real safety regression: applying a generic line-length cap to holding actions could remove the exit condition. The final implementation uses a dedicated commuter holding formatter that preserves judgment, today's action, and exit condition while removing repeated risk-method prose.

## Boundary Checks

- The report still reads `latest.md`, `latest_decisions.json`, `pipeline.status`, announcements, and the caller-provided holdings path.
- The stale execution guard remains the first quick-read item and appears before holdings and candidates.
- Candidate ranking is capped for email presentation only; full candidates and evidence remain in reports and web workspaces.
- `send_user_morning_reports.py`, per-user scheduling, recipient configuration, and dispatch behavior are unchanged.
- Server verification used `--dry-run`; no real email was sent.

## Residual Risks

- Exact typography depends on the existing email client's Markdown renderer; content density is verified at the Markdown contract layer.
- Only the most actionable data/announcement exception appears in `三条纪律`; remaining evidence intentionally stays in the data workspace.

## Decision

Accept for fast-forward integration after final full-suite baseline comparison.
