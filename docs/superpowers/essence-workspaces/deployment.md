# Essence Workspaces Deployment Evidence

## Deployment

- Deployed implementation commit: `dee3e7e732016398b30013f1f9af1e6294e85978`
- Branch: `main`
- Server checkout: `/opt/stock-ts`
- Server backup: `/opt/stock-ts/.deploy_backups/essence-workspaces-20260714125331`
- Transfer: verified Git bundle followed by `git merge --ff-only`
- Preserved runtime paths: `.env`, `.secrets`, `data`, `reports`

After deployment, `stock-ts.service`, `stock-ts-signal-desk.service`, both StockTS timers, and Nginx were active. Server-local `/healthz` and public `/healthz` returned HTTP 200.

## Production Refresh

The production daily-analysis service was started after deployment.

Successful steps:

```text
refresh=ok
tdx_enrich=ok
a_share_kline=ok
external_enrich=ok
announcements=ok
report=ok
```

Refresh output:

- full-market scan: 5,533 stocks;
- candidate pool: 300 stocks;
- Tushare K-line refresh: 311 requested, 310 updated, 0 failed, 1 non-A-share skipped;
- market news observed during enrichment: 125 items;
- latest daily report: `status=ok`, `trade_date=2026-07-14`, generated at `2026-07-14T13:21:11`.

The final pipeline status is intentionally `failed` at the data-chain hard gate. At 13:21 during the open 2026-07-14 trading session, daily K-lines correctly ended at the last completed trading day, 2026-07-13, while the validator required 2026-07-14. The refreshed report and data artifacts exist, but StockTS correctly pauses current-price actions instead of treating an unfinished daily bar as complete evidence.
