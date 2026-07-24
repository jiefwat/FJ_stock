# Advanced Equity Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add server-side advanced full-market filters and reusable account-scoped saved views to the Market page.

**Architecture:** Keep filtering deterministic in `MarketService`, persistence in `Store`, and expose only `/api/v1/*` contracts. Treat the URL as the active filter state in React and saved views as validated snapshots of that state without page numbers.

**Tech Stack:** FastAPI, Pydantic, SQLite, React, React Router, TanStack Query, Vitest, Testing Library.

---

### Task 1: Server-side advanced filters

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`
- Test: `backend/tests/test_api.py`

- [ ] Add an API test that combines sector, minimum change, amount, turnover, market cap, and complete-data filters and asserts filtered totals, ordering, pagination, and available sectors.
- [ ] Run `cd backend && uv run pytest tests/test_api.py -k advanced_equity_filters -q` and confirm it fails because the query parameters are not accepted or applied.
- [ ] Add optional validated query parameters, pass them to `MarketService.equities_page`, apply AND semantics, and expose sorted real sector options on `EquityPage`.
- [ ] Add validation for inverted numeric bounds and confirm FastAPI returns 422 rather than silently accepting an impossible range.
- [ ] Run the targeted backend tests and confirm they pass.

### Task 2: Account-scoped saved views

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/store.py`
- Modify: `backend/src/marketdesk/api.py`
- Test: `backend/tests/test_store.py`
- Test: `backend/tests/test_api.py`

- [ ] Add failing store and API tests for create/list/delete, duplicate names, validated filter payloads, and cross-account isolation.
- [ ] Run `cd backend && uv run pytest tests/test_store.py tests/test_api.py -k equity_view -q` and confirm the new tests fail because persistence and routes do not exist.
- [ ] Create `saved_equity_views` with `UNIQUE(user_id,name)` and foreign-key cascade, then implement typed store CRUD.
- [ ] Add `GET`, `POST`, and `DELETE /api/v1/equity-views` routes using the existing current-user boundary.
- [ ] Run the targeted backend tests and confirm they pass.

### Task 3: URL-driven advanced filter UI

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/features/market/EquityBrowser.tsx`
- Modify: `frontend/src/features/market/MarketPage.test.tsx`
- Modify: `frontend/src/app/styles.css`

- [ ] Add a failing component test that enters advanced ranges, verifies URL/API unit conversion, resets filters, and restores state from URL search parameters.
- [ ] Run `cd frontend && pnpm test --run src/features/market/MarketPage.test.tsx` and confirm the new assertions fail because the controls do not exist.
- [ ] Define typed filter and saved-view contracts in `api.ts`; parse valid URL values once and derive the request query from that state.
- [ ] Build the collapsible filter grid with explicit units, range validation, active-count feedback, complete-data toggle, empty state, and reset action.
- [ ] Preserve the existing dense table and responsive toolbar behavior, then run the targeted component tests.

### Task 4: Saved-view interaction

**Files:**
- Modify: `frontend/src/features/market/EquityBrowser.tsx`
- Modify: `frontend/src/features/market/MarketPage.test.tsx`
- Modify: `frontend/src/app/styles.css`

- [ ] Add failing tests for loading views, saving current conditions, applying a view from page 1, duplicate/error feedback, and deleting a view.
- [ ] Run the targeted Vitest command and confirm failure for missing view controls.
- [ ] Add TanStack Query and mutation flows for list/create/delete, disable duplicate submits, preserve input on errors, and invalidate only the saved-view query.
- [ ] Run the targeted component tests and confirm all advanced-filter and saved-view cases pass.

### Task 5: Verification and release

**Files:**
- Modify: `docs/superpowers/market-intelligence-workbench/TODO.md`
- Modify: `docs/superpowers/market-intelligence-workbench/test.md`

- [ ] Run backend and frontend targeted tests, then run `make verify` and record the fresh totals.
- [ ] Start the production build locally and smoke-test filter, URL reload, save/apply/delete, empty state, and responsive layout in a real browser.
- [ ] Commit the verified implementation with a Chinese scope message and push `codex/user-accounts-personalization`.
- [ ] Deploy through `deploy/deploy_public.sh` to `stock.jiewat-kaka-fj.com` and verify health, advanced filter response, saved-view authentication boundary, and the Market page.
- [ ] Record the release ID and public evidence in `test.md`, check the working tree, and push the release record.
