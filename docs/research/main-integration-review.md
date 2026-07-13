# Main Integration Review

**Date:** 2026-07-13

**Range:** `origin/main@a3690a9..codex/research-data-depth@8cda8b4`

**Purpose:** Fast-forward the verified market and stock research upgrades into `main`, then align the production application source with that branch.

## Findings

### Resolved P1 - Python 3.9 compatibility

`src/stock_ts/research/evidence.py` imported `enum.StrEnum`, which is only available in Python 3.11 and newer, while `pyproject.toml` declares Python `>=3.9` and targets `py39` in Ruff. This caused test collection and application imports to fail under the repository's existing Python 3.9 virtual environment.

The integration changes `EvidenceStatus` to a `str` and `Enum` subclass with the same string-value behavior. `tests/test_python_compatibility.py` runs the import in a subprocess using the active supported interpreter and verifies that `str(EvidenceStatus.COMPLETE)` remains `complete`.

No unresolved P0 or P1 finding remains in the integration diff.

## Verification

```text
Python 3.9 focused research suite: 83 passed
Python 3.9 full suite: 498 passed, 6 failed, 10 warnings
Python 3.11 full suite: 498 passed, 6 failed, 11 warnings
Ruff: All checks passed
```

The six full-suite failures are unchanged from the Phase 1 and Phase 2 baseline:

1. five daily-pipeline tests whose mocked step contract predates the current pipeline;
2. one stale-opportunity copy assertion whose expected wording predates the current hard data gate.

## Open Questions And Assumptions

- Production runs Python 3.12, but keeping the declared Python 3.9 compatibility avoids breaking existing local environments.
- The server deployment must preserve ignored runtime data, credentials, account holdings, reports, timers, and Nginx configuration.
- Server tracked source must be backed up before replacing historical incremental patches with the new `main` tree.

## Residual Risks And Testing Gaps

- The six known baseline failures still prevent describing the repository-wide suite as green.
- External market providers remain network- and rate-limit-dependent; this integration verification uses deterministic unit tests and the existing local snapshot.
- Public production verification must be repeated after the server is aligned to `main`.

## Decision

The research branch is safe to integrate into `main` after the compatibility fix. Production alignment remains conditional on a complete rollback backup, source reconciliation, service restart, and public-route verification.
