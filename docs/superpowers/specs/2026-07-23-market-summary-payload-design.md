# Market Summary Payload Design

Date: 2026-07-23
Status: Approved under delegated product authority

## Decision

The `/api/v1/market` route will return only the market summary consumed by the Market page: dataset metadata, indices, sectors, and deterministic market analysis. It will no longer serialize the full A-share equity universe into the browser response.

## Rationale

The production endpoint currently sends about 1.4 MB because `MarketSnapshot` includes roughly 5,500 equity quotes. The Market page does not read those quotes; full-universe data remains an internal input for market analysis, opportunity ranking, search, stock dossiers, and holding analysis. Removing it from this response reduces network transfer and JSON parsing without changing visible conclusions.

## Contract

- Add explicit `MarketSummarySnapshot` and `MarketPayload` response models.
- Keep `MarketService.market()` returning the full internal `MarketSnapshot`.
- Make `MarketService.market_payload()` project the internal snapshot into the summary model.
- Keep browser code dependent only on `/api/v1/*`; no provider access moves into the frontend.
- Keep `/api/v1/search`, `/api/v1/opportunities`, `/api/v1/stocks/*`, and `/api/v1/holdings` behavior unchanged.

## Error Handling

The summary inherits the same metadata, freshness, coverage, and provider errors as the internal snapshot. Cached-snapshot fallback remains in `MarketService.market()` and is unchanged.

## Acceptance

- `/api/v1/market` still returns metadata, indices, sectors, and analysis.
- The response `snapshot` does not contain `equities`.
- Market analysis still uses the complete equity universe before projection.
- Backend tests and the repository `make verify` gate pass.
- The production endpoint returns the compact contract after deployment.
