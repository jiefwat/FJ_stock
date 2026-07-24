# Full Market Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bounded full-market browsing with search, ranking, pagination, and direct Stock Lab navigation.

**Architecture:** The service filters and sorts its cached full `MarketSnapshot`, then returns an explicit `EquityPage` contract through `/api/v1/equities`. A focused React component owns quote-browser state so failures never hide the existing Market page.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest, React 19, TypeScript, TanStack Query, Vitest, Testing Library

---

## File Map

- `backend/src/marketdesk/models.py`: define the bounded page response.
- `backend/src/marketdesk/services.py`: filter, sort with missing values last, and slice the cached universe.
- `backend/src/marketdesk/api.py`: validate query parameters and expose `/api/v1/equities`.
- `backend/tests/test_api.py`: lock search, sorting, pagination, and missing-value behavior.
- `frontend/src/lib/api.ts`: type the equity page contract.
- `frontend/src/features/market/EquityBrowser.tsx`: isolate browser query and interaction state.
- `frontend/src/features/market/MarketPage.tsx`: mount the browser without coupling it to the summary query.
- `frontend/src/features/market/MarketPage.test.tsx`: cover browsing, sorting, searching, and navigation.
- `frontend/src/app/styles.css`: add compact responsive quote-browser styles.

### Task 1: Paginated Equity API

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`

- [x] **Step 1: Write the failing API test**

Add a provider with three equities, including one missing `amount`, then assert:

```python
response = api.get(
    "/api/v1/equities",
    params={"sort_by": "amount", "direction": "desc", "page": 1, "page_size": 2},
)
payload = response.json()
assert payload["total"] == 3
assert [item["symbol"] for item in payload["items"]] == ["SH.600519", "SZ.000001"]
assert "equities" not in payload

missing_last = api.get(
    "/api/v1/equities",
    params={"sort_by": "amount", "direction": "asc", "page": 1, "page_size": 3},
).json()
assert missing_last["items"][-1]["amount"] is None

search = api.get("/api/v1/equities", params={"q": "茅台"}).json()
assert search["total"] == 1
assert search["items"][0]["symbol"] == "SH.600519"
```

- [x] **Step 2: Verify the API test is RED**

Run: `cd backend && uv run pytest -q tests/test_api.py::test_equity_browser_searches_sorts_and_paginates`

Expected: FAIL with HTTP 404 because `/api/v1/equities` does not exist.

- [x] **Step 3: Implement the explicit page contract**

Add:

```python
class EquityPage(StrictModel):
    meta: DatasetMeta
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=50)
    sort_by: str
    direction: str
    items: list[EquityQuote]
```

Implement `MarketService.equities_page(...)` to normalize `q`, keep missing numeric values after present values in both directions, and return the requested slice. Add the FastAPI route using `Literal` query types, `page >= 1`, and `1 <= page_size <= 50`.

- [x] **Step 4: Verify the API test is GREEN**

Run: `cd backend && uv run pytest -q tests/test_api.py::test_equity_browser_searches_sorts_and_paginates`

Expected: PASS.

### Task 2: Market Page Quote Browser

**Files:**
- Modify: `frontend/src/features/market/MarketPage.test.tsx`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/features/market/EquityBrowser.tsx`
- Modify: `frontend/src/features/market/MarketPage.tsx`
- Modify: `frontend/src/app/styles.css`

- [x] **Step 1: Write the failing interaction test**

Return a typed equity-page fixture from `/api/v1/equities`, then assert:

```tsx
expect(await screen.findByText("全市场行情")).toBeInTheDocument();
expect(screen.getByRole("link", { name: /贵州茅台/ })).toHaveAttribute(
  "href",
  "/stocks?symbol=SH.600519",
);
fireEvent.change(screen.getByLabelText("排序字段"), { target: { value: "change_pct" } });
await waitFor(() => expect(requests.some((url) => url.includes("sort_by=change_pct"))).toBe(true));
fireEvent.change(screen.getByLabelText("搜索全市场"), { target: { value: "茅台" } });
fireEvent.click(screen.getByRole("button", { name: "搜索" }));
await waitFor(() => expect(requests.some((url) => url.includes("q=%E8%8C%85%E5%8F%B0"))).toBe(true));
```

- [x] **Step 2: Verify the UI test is RED**

Run: `cd frontend && pnpm test --run src/features/market/MarketPage.test.tsx`

Expected: FAIL because the full-market browser is not rendered.

- [x] **Step 3: Implement the isolated browser component**

Create `EquityBrowser` with draft and submitted search state, sort and direction selects, one-based pagination, panel-local loading/error feedback, a six-column quote table, and stock links. Add the `EquityPage` TypeScript type and mount the component after the breadth/evidence section.

- [x] **Step 4: Add bounded responsive styles**

Add `.equity-browser`, `.equity-toolbar`, `.equity-table`, and `.equity-pagination` styles. Keep the table readable at the repository desktop minimum, allow controlled horizontal scrolling for narrower viewports, and preserve visible keyboard focus.

- [x] **Step 5: Verify the UI test is GREEN**

Run: `cd frontend && pnpm test --run src/features/market/MarketPage.test.tsx`

Expected: PASS.

### Task 3: Verification And Release

**Files:**
- Modify: `docs/superpowers/market-intelligence-workbench/TODO.md`
- Modify: `docs/superpowers/market-intelligence-workbench/test.md`
- Modify: `docs/superpowers/market-intelligence-workbench/review.md`

- [x] **Step 1: Run the complete repository gate**

Run: `make verify`

Expected: backend lint, types, tests, frontend types, tests, build, and live-data quality all pass.

- [x] **Step 2: Record review and verification evidence**

Document the red-green tests, final counts, API boundaries, residual risks, and review decision. Mark the active TODO only after the full gate passes.

- [ ] **Step 3: Commit, push, and deploy**

Create a traceable Chinese-scope commit, push `codex/user-accounts-personalization`, and deploy through `deploy/deploy_public.sh` with the existing host and SSH key.

- [ ] **Step 4: Smoke-test production**

Verify health, default pagination, name search, both sort directions, missing-value placement, response bounds, production release pointer, and service activity. Confirm the public Market page still loads its compact summary independently.
