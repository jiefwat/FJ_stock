# Market Summary Payload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the unused full-equity universe from `/api/v1/market` while preserving the Market page contract and internal analysis inputs.

**Architecture:** Keep `MarketSnapshot` as the internal full-universe model. Add an explicit browser-facing summary response and project into it only after deterministic analysis has run.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest

---

### Task 1: Enforce a compact market response

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`

- [x] **Step 1: Write the failing contract test**

Extend `test_market_today_and_stock_routes` with:

```python
market_payload = market.json()
assert market_payload["snapshot"]["meta"]["source"] == "fixture"
assert market_payload["snapshot"]["indices"][0]["symbol"] == "SH.000001"
assert market_payload["snapshot"]["sectors"][0]["code"] == "BK1"
assert "equities" not in market_payload["snapshot"]
```

- [x] **Step 2: Run the focused test to verify RED**

Run: `cd backend && uv run pytest -q tests/test_api.py::test_market_today_and_stock_routes`

Expected: FAIL because the current route serializes `MarketSnapshot.equities`.

- [x] **Step 3: Add the minimal summary contract**

Add `MarketSummarySnapshot` with `meta`, `indices`, and `sectors`, plus `MarketPayload` with `snapshot` and `analysis`. Change `market_payload()` to construct the summary after calling `analyse_market(snapshot)`, and declare `response_model=MarketPayload` on the route.

- [x] **Step 4: Run the focused test to verify GREEN**

Run: `cd backend && uv run pytest -q tests/test_api.py::test_market_today_and_stock_routes`

Expected: PASS.

- [ ] **Step 5: Run full verification and measure the endpoint**

Run: `make verify`, deploy with `deploy/deploy_public.sh`, then request `https://stock.jiewat-kaka-fj.com/api/v1/market` and confirm HTTP 200, the absence of `snapshot.equities`, and a materially smaller response body.
