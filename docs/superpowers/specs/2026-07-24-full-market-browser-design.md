# Full Market Browser Design

Date: 2026-07-24
Status: Approved under delegated product authority

## 1. Decision

Add a server-paginated full-market quote browser to the Market page. The feature makes the complete A-share universe inspectable without restoring the previous 1.4 MB full-universe payload to the market-summary request.

## 2. Alternatives Considered

1. Restore all equities to `/api/v1/market`: simplest wiring, but every Market-page visit downloads and parses thousands of unused rows.
2. Add search only: lightweight, but it does not let the user browse or rank the market.
3. Add a dedicated paginated endpoint and browser: selected because it supports both discovery and direct lookup while keeping transfers bounded.

## 3. API Contract

`GET /api/v1/equities` accepts:

- `q`: optional stock code or name fragment;
- `sort_by`: `amount`, `change_pct`, `turnover_rate`, or `market_cap`;
- `direction`: `asc` or `desc`;
- `page`: one-based page number;
- `page_size`: 1 through 50, default 25.

The response contains snapshot metadata, total matching rows, current page, page size, sort settings, and the bounded `items` list. Rows with missing sort evidence always appear after rows with real values. Requests for pages beyond the result set return an empty list with the true total rather than silently changing the requested page.

## 4. Page Interaction

Add an `全市场行情` panel to the Market page after the market evidence summary. It contains:

- a search field and explicit search action;
- sort-field and direction controls;
- a compact table with stock, price, change, turnover, amount, and market value;
- a result count plus previous/next pagination;
- stock names linking directly to Stock Lab.

Changing sort or direction resets to page 1. Search is submitted rather than fired on every keystroke. Loading and error feedback stay inside the quote panel so the existing market summary remains usable.

## 5. Boundaries

- Provider access stays under `backend/src/marketdesk/providers/`.
- Filtering, sorting, and pagination operate on the cached `MarketSnapshot` in the service layer.
- Browser code calls only `/api/v1/*`.
- The existing `/api/v1/market` compact response remains unchanged.

## 6. Acceptance

- The API can find a stock by code or Chinese name.
- Numeric sorting is deterministic and missing values remain last in both directions.
- Every response contains at most `page_size` rows.
- The Market page can browse forward and back, change ranking, search, and open Stock Lab.
- The feature remains usable when its own request fails.
- `make verify` passes and production smoke checks confirm pagination against the live full-market snapshot.
