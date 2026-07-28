# A-share Evidence And Market Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cited A-share company evidence and market intelligence from the reviewed upstream API catalog while preserving StockTs's deterministic analysis and current API compatibility.

**Architecture:** Introduce strict evidence/intelligence models and a focused provider under `backend/src/marketdesk/providers/`. Compose it through `PublicMarketProvider`, cache normalized results in `MarketService`, and expose authenticated `/api/v1/instruments/*` and `/api/v1/markets/CN/*` routes. Render those APIs in Stock Lab, Market, and Data Center without feeding display-only data into scores.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, httpx, pytest, React 19, TypeScript, TanStack Query, Vitest, Testing Library.

---

## File Map

- `backend/src/marketdesk/models.py`: strict source, document, theme, anomaly, and result contracts.
- `backend/src/marketdesk/providers/cn_evidence.py`: CNINFO, Eastmoney report/theme/Dragon-Tiger, and CLS adapters.
- `backend/src/marketdesk/providers/public_market.py`: compose the focused provider and implement event fallback/status aggregation.
- `backend/src/marketdesk/services.py`: A-share validation, normalized TTL caches, and service orchestration.
- `backend/src/marketdesk/api.py`: new authenticated evidence and CN intelligence routes.
- `backend/tests/test_cn_evidence_provider.py`: payload normalization and request-contract tests.
- `backend/tests/test_api.py`: partial-result, cache, route, and authentication contract tests.
- `frontend/src/lib/api.ts`: typed evidence/intelligence contracts.
- `frontend/src/features/stocks/StockLabPage.tsx`: cited filings, reports, and themes.
- `frontend/src/features/stocks/StockLabPage.test.tsx`: evidence rendering and unavailable-state tests.
- `frontend/src/features/market/MarketPage.tsx`: sector-flow and Dragon-Tiger intelligence.
- `frontend/src/features/market/MarketPage.test.tsx`: market-intelligence rendering tests.
- `frontend/src/features/data/DataCenterPage.tsx`: capability labels and status explanation.
- `frontend/src/app/styles.css`: evidence and intelligence layout styles.

### Task 1: Strict Evidence Contracts

- [ ] Write model tests proving timezone-aware sources, typed document kinds, and bounded freshness/status fields.
- [ ] Run the focused tests and confirm they fail because the contracts do not exist.
- [ ] Add `SourceRef`, `EvidenceDocument`, `InstrumentTheme`, `TradingAnomaly`, `CapabilityState`, `InstrumentEvidenceResult`, and `MarketIntelligenceResult`.
- [ ] Run model tests and backend type checks.

### Task 2: Provider Normalization And Fallback

- [ ] Write fixture tests for CNINFO org mapping and announcements, Eastmoney report/theme/Dragon-Tiger payloads, and CLS signed-response normalization.
- [ ] Run the provider tests and confirm the missing provider failure.
- [ ] Implement `AshareEvidenceProvider` with bounded requests, strict parsing, source attribution, and capability status updates.
- [ ] Add `PublicMarketProvider` composition and Eastmoney-to-CLS event fallback.
- [ ] Run provider tests and existing public-provider tests.

### Task 3: Service Cache And APIs

- [ ] Write API tests for `/api/v1/instruments/{symbol}/evidence`, `/api/v1/markets/CN/intelligence`, authentication, partial results, and repeated-request TTL behavior.
- [ ] Run focused API tests and confirm 404/missing-method failures.
- [ ] Implement A-share symbol validation, per-capability in-memory TTL caching, partial aggregation, and new routes.
- [ ] Include new capability health in `/api/v1/data-status` without changing existing fields.
- [ ] Run backend tests, lint, and mypy.

### Task 4: Stock Lab Evidence UI

- [ ] Write failing Stock Lab tests for source links, filing/report grouping, themes, and explicit unavailable source messages.
- [ ] Run the focused test and confirm the evidence panel is absent.
- [ ] Add typed API models and the evidence query, preserving the existing dossier query if evidence fails.
- [ ] Render compact cited evidence cards and theme tags; label reports as context that does not alter scores.
- [ ] Run the Stock Lab test, frontend typecheck, and frontend tests.

### Task 5: Market Intelligence And Data Status UI

- [ ] Write failing Market/Data Center tests for flow leaders, Dragon-Tiger observations, and new capability labels.
- [ ] Run the focused tests and confirm the panels/labels are absent.
- [ ] Query and render CN intelligence in Market with a bounded list and explicit source status.
- [ ] Add capability labels and licensing/context copy to Data Center.
- [ ] Run all frontend tests, typecheck, and production build.

### Task 6: Verification, Deployment, And Handoff

- [ ] Update the active requirement TODO and verification evidence for the new release.
- [ ] Run `make verify` and fix only integration-related failures.
- [ ] Start the production build with `make start` and verify health plus authenticated Stock Lab, Market, and Data Center workflows.
- [ ] Run `git diff --check`, inspect the final diff, commit the release, and push the current branch.
- [ ] Record the deployed URL, version commit, `v2` rollback commands, provider limitations, and test counts.

