# Handoff

Status: implementation and local verification complete; pending merge, push, and deployment.

## Delivered

- `每日大盘`: one primary market verdict plus a five-step risk decision rail.
- `我的持仓`: one portfolio risk verdict, ordered treatment queue, exposure register, and per-position boundaries.
- `热点机会`: one opportunity gate, evidence funnel, risk exclusions, and research-only candidates.
- Stale/blocked data now propagates from market to portfolio and opportunity without leaking active price actions or rankings.

## Integration Boundary

- Merge into `main` only after the final branch diff, lint, focused tests, and recorded full-suite baseline comparison are clean.
- Deploy tracked source only; preserve server `.env`, `.secrets`, snapshots, holdings, reports, Nginx, systemd services/timers, and DSA.
- Verify local `main`, GitHub `origin/main`, and server HEAD are identical after deployment.
