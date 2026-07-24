# Full-Market Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the complete A-share quote browser practical to navigate through exchange filtering, selectable page size, direct page entry, and first/last controls.

**Architecture:** Extend the explicit `EquityPage` contract with a typed exchange discriminator and filter the cached snapshot before the existing deterministic sort. Keep navigation state inside `EquityBrowser`, using native form controls and TanStack Query keys so every server-visible state change is independently cached and bounded.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest, React 19, TypeScript, TanStack Query, Vitest, Testing Library

---

## File Map

- `backend/src/marketdesk/models.py`: echo the effective exchange in the page contract.
- `backend/src/marketdesk/services.py`: combine exchange and text filtering before sorting.
- `backend/src/marketdesk/api.py`: validate the new query parameter.
- `backend/tests/test_api.py`: prove exchange filtering and compatibility.
- `frontend/src/lib/api.ts`: type the exchange contract.
- `frontend/src/features/market/EquityBrowser.tsx`: own exchange, page-size, and jump state.
- `frontend/src/features/market/MarketPage.test.tsx`: prove request and navigation behavior.
- `frontend/src/app/styles.css`: compose the added controls without weakening focus or table readability.

### Task 1: Exchange-Filtered Page Contract

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`

- [x] **Step 1: Write the failing API assertions**

Add a `BJ.430047` quote to `EquityBrowserProvider`. Extend `test_equity_browser_searches_sorts_and_paginates` to assert that `exchange=bj` returns only that quote, `exchange=sz&q=000001` returns only Ping An Bank, and the default response echoes `exchange=all`.

- [x] **Step 2: Verify RED**

Run: `cd backend && uv run pytest -q tests/test_api.py::test_equity_browser_searches_sorts_and_paginates`

Expected: FAIL because the response does not contain `exchange` and the route ignores the filter.

- [x] **Step 3: Implement the typed filter**

Add `exchange: Literal["all", "sh", "sz", "bj"]` to `EquityPage`, accept the same typed query parameter in the route, and pass it to `MarketService.equities_page`. In the service, keep a quote when `exchange == "all"` or its symbol starts with `f"{exchange.upper()}."`; combine this with the existing text predicate before sorting.

- [x] **Step 4: Verify GREEN**

Run the focused pytest command from Step 2.

Expected: one passing test.

### Task 2: Practical Market Navigation

**Files:**
- Modify: `frontend/src/features/market/MarketPage.test.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/features/market/EquityBrowser.tsx`
- Modify: `frontend/src/app/styles.css`

- [x] **Step 1: Write the failing interaction assertions**

Extend the fixture with `exchange: "all"`. Assert that selecting `bj` sends `exchange=bj&page=1`, selecting page size 50 sends `page_size=50&page=1`, submitting page 2 sends `page=2`, and the last-page button sends the current calculated last page. Use accessible labels `交易所`, `每页数量`, and `跳转页码`.

- [x] **Step 2: Verify RED**

Run: `cd frontend && pnpm test --run src/features/market/MarketPage.test.tsx`

Expected: FAIL because the new labelled controls do not exist.

- [x] **Step 3: Implement navigation state**

Add `EquityExchange`, include exchange and page size in the query key and URL, reset page 1 when either changes, derive the visible row range, and render native exchange/page-size selects. Add first/last buttons and a numeric jump form that parses and clamps values to `1..totalPages`; synchronize the draft whenever page or total pages changes.

- [x] **Step 4: Style the controls**

Extend the existing `.equity-rank-controls` and `.equity-pagination` rules. Keep controls at least 36 CSS pixels high, show visible focus through the repository global rule, and allow the footer controls to wrap instead of causing document overflow.

- [x] **Step 5: Verify GREEN**

Run the focused Vitest command from Step 2.

Expected: both Market page tests pass.

### Task 3: Verification And Release

**Files:**
- Modify: `docs/superpowers/market-intelligence-workbench/TODO.md`
- Modify: `docs/superpowers/market-intelligence-workbench/test.md`
- Modify: `docs/superpowers/market-intelligence-workbench/review.md`

- [x] **Step 1: Run `make verify`**

Expected: backend lint, mypy, pytest, frontend types, Vitest, production build, and live-data quality all pass.

- [x] **Step 2: Record evidence and review**

Document red-green evidence, test counts, contract compatibility, missing-data behavior, and the production smoke checklist. Mark the active TODO only after the full gate passes.

- [x] **Step 3: Commit, push, and deploy**

Use Chinese-scope commits, push `codex/user-accounts-personalization`, and deploy with `deploy/deploy_public.sh` to `stock.jiewat-kaka-fj.com`.

- [x] **Step 4: Smoke-test production**

Check health, non-empty `sh`, `sz`, and `bj` responses, combined search, page-size 50, direct page 2, service status, persisted holdings/watchlist, and the full interaction in real Chrome.
