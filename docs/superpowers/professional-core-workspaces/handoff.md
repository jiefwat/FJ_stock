# Handoff

Status: merged to `main`, pushed, deployed, and verified.

## Delivered

- `每日大盘`: one primary market verdict plus a five-step risk decision rail.
- `我的持仓`: one portfolio risk verdict, ordered treatment queue, exposure register, and per-position boundaries.
- `热点机会`: one opportunity gate, evidence funnel, risk exclusions, and research-only candidates.
- Stale/blocked data now propagates from market to portfolio and opportunity without leaking active price actions or rankings.

## Integration Boundary

- Merge into `main` only after the final branch diff, lint, focused tests, and recorded full-suite baseline comparison are clean.
- Deploy tracked source only; preserve server `.env`, `.secrets`, snapshots, holdings, reports, Nginx, systemd services/timers, and DSA.
- Verify local `main`, GitHub `origin/main`, and server HEAD are identical after deployment.

## Deployment Result

- Code release commit: `212b22684c3ce5ac0193fb392f183b980c47369e`.
- Server: `admin@47.82.145.207`, `/opt/stock-ts`, branch `main`.
- Backup: `.deploy_backups/20260713-192045-ac9ff65/source-ac9ff65.tar.gz`.
- `stock-ts.service`, `stock-ts-signal-desk.service`, and Nginx remained active.
- Server and public `/healthz` returned HTTP 200; the public root correctly redirected to the protected login page.
- `.env`, `.secrets`, data, reports, timers, Nginx configuration, and the separate DSA deployment were not replaced.
