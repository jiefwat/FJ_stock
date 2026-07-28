# A-share Evidence And Market Intelligence Design

Date: 2026-07-28
Status: Approved by user selection of bundle `0 + 1 + 2`

## 1. Decision

Build the first production-safe slice of the `a-stock-data` integration behind StockTs's existing provider boundary. The release adds typed, source-attributed A-share company evidence and market intelligence without importing the upstream repository as a runtime dependency.

The existing A-share quote, K-line, analysis, authentication, holdings, watchlist, and browser-facing APIs remain compatible. External documents, themes, flow rankings, and trading anomalies are evidence only; they do not directly change deterministic stock or opportunity scores.

## 2. Release Scope

### 2.1 Evidence foundation

- Add strict `SourceRef`, `EvidenceDocument`, `InstrumentTheme`, `CorporateEvent`, and capability-result contracts.
- Every item carries provider, source label, source URL when available, observed time, fetched time, freshness, and a stable provider item ID.
- Distinguish `ready`, `partial`, `empty`, and `unavailable`; an upstream failure must not be presented as a valid empty result.
- Split document and intelligence provider protocols by capability while retaining the existing `PublicMarketProvider` composition and all current APIs.
- Cache only normalized in-memory results for a short TTL. Do not persist raw provider payloads or PDF bodies.

### 2.2 A-share company evidence

- Query CNINFO announcements for a single A-share symbol, resolving the official `orgId` mapping before querying.
- Query Eastmoney research-report metadata for a single A-share symbol.
- Return document title, category, publisher, published time, source link, optional rating and EPS forecasts.
- Expose `GET /api/v1/instruments/{symbol}/evidence?limit=20`.
- Show the result in Stock Lab as two cited streams: company filings and research reports.
- Never download a report PDF automatically; outbound links open the source in a new tab.

### 2.3 A-share market intelligence

- Retain existing Eastmoney sector-flow enrichment and expose its source/status explicitly.
- Fetch Eastmoney concept-board membership for a selected instrument.
- Fetch the latest available daily Dragon-Tiger list through Eastmoney's data-center endpoint.
- Add CLS telegraph as an independent fallback when Eastmoney fast news fails or returns no usable events.
- Expose `GET /api/v1/markets/CN/intelligence?limit=20` for sector flows and Dragon-Tiger entries; instrument themes are included in the evidence endpoint.
- Show sector-flow leaders and Dragon-Tiger observations in Market; show themes in Stock Lab.

## 3. Provider And Data Flow

`AshareEvidenceProvider` owns CNINFO, Eastmoney report metadata, Eastmoney concept membership, Eastmoney Dragon-Tiger data, and CLS news normalization. `PublicMarketProvider` composes it and continues to own quotes, bars, sector snapshots, and existing market events.

The request path is:

1. Browser calls authenticated `/api/v1/*` routes.
2. `MarketService` validates the A-share symbol and reads the capability TTL cache.
3. On cache miss, the capability provider performs bounded requests with provider-specific headers and timeouts.
4. Provider payloads are validated and normalized into strict models.
5. The service returns normalized results plus capability-level status. Partial provider failures remain visible and successful streams remain usable.

The provider never calls analysis code. Deterministic analysis remains under `backend/src/marketdesk/analysis/` and does not consume the new display-only fields in this release.

## 4. Error And Freshness Behaviour

- CNINFO mapping failure uses its documented legacy `orgId` fallback and marks the source partial if the query still succeeds.
- One failed company-evidence source does not hide the other source. The API returns the successful items and a source-scoped error.
- Eastmoney and CLS failures remain isolated. Market events use Eastmoney first and CLS only when Eastmoney is empty or unavailable.
- A successful response with zero rows is `empty`; transport, schema, or parsing failure is `unavailable`.
- Company evidence uses a 15-minute normalized TTL; market intelligence uses a 10-minute TTL; no raw payload is persisted.
- Provider status in Data Center is capability-specific, including the latest error and whether the source is required.

## 5. Security, Licensing, And Product Boundaries

- All provider calls stay server-side and use no browser-visible credentials.
- Upstream repositories are referenced at fixed commits as implementation research only; their `SKILL.md` files are not installed or imported.
- This deployment is for local/personal research. Public or commercial deployment requires a fresh review of CNINFO, Eastmoney, and CLS terms.
- Report and announcement links are source references, not mirrored content. No PDF or full document is cached.
- Dragon-Tiger data, supplier flow algorithms, themes, and report ratings are labelled as observations and never described as trading advice.

## 6. Acceptance

- `v2` remains a remote rollback tag pointing to the pre-integration commit.
- Existing A-share APIs and all current tests remain compatible.
- A Stock Lab request can display current announcements, report metadata, and themes with source and timestamps.
- Market can display sector-flow leaders and the latest available Dragon-Tiger observations.
- Eastmoney news failure can fall back to CLS without turning an upstream error into an empty-success state.
- Data Center identifies each new capability separately and shows ready/partial/empty/unavailable status.
- Provider fixture tests cover schema drift, empty payloads, invalid timestamps, and fallback selection.
- Frontend tests cover cited evidence, partial/unavailable states, and market-intelligence rendering.
- `make verify` passes, then the production build starts locally and the authenticated workflow is checked in a real browser.

