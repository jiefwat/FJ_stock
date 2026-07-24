# Full-Market Navigation Design

Date: 2026-07-24
Status: Approved under delegated product authority

## 1. Problem

The full-market browser exposes all 5,000-plus A-share quotes, but a 25-row page with only previous and next buttons still requires more than 200 sequential actions to reach the end. It also cannot isolate Shanghai, Shenzhen, or Beijing listings, so users cannot verify whether the advertised full market includes each exchange.

## 2. Decision

Upgrade the existing browser with three connected navigation capabilities:

- filter the complete cached universe by `全部`, `沪市`, `深市`, or `北交所`;
- choose 25 or 50 rows per page;
- jump directly to a validated page while retaining first, previous, next, and last navigation.

This is preferred over adding valuation thresholds now. Exchange and page navigation are exact structural facts, while valuation filters would amplify the effect of missing or stale evidence and need a separate screener design.

## 3. API Contract

`GET /api/v1/equities` adds an `exchange` parameter with `all | sh | sz | bj`, defaulting to `all`. Filtering occurs before sorting and pagination. `EquityPage` echoes the effective exchange so clients can verify the response contract.

The existing `q`, `sort_by`, `direction`, `page`, and `page_size` behavior remains compatible. A search and an exchange filter combine with logical AND. Missing numeric values remain last after filtering.

## 4. Interaction

The quote panel adds a clearly labelled native exchange select next to the existing ranking controls. Changing exchange or page size resets to page 1. The footer reports the visible row range, filtered total, and current page.

Pagination uses semantic buttons for first, previous, next, and last. A labelled numeric input and submit button allow direct page entry. Submitted page values are clamped to the valid range, and the displayed draft is synchronized after other navigation actions. Native controls preserve keyboard and assistive-technology behavior without introducing a custom composite widget.

## 5. Boundaries

- Exchange membership is derived only from normalized symbol prefixes `SH.`, `SZ.`, and `BJ.`.
- Provider access and snapshot acquisition remain unchanged.
- Browser requests remain under `/api/v1/*`.
- Filters are session-local; URL persistence and an advanced factor screener remain out of scope.

## 6. Acceptance

- Backend tests prove each exchange filter, combined search, response echo, and backward-compatible default behavior.
- Frontend tests prove exchange and page-size resets, direct page jump, first/last navigation, bounded page submission, and request parameters.
- The complete repository gate passes.
- Production smoke confirms non-empty Shanghai, Shenzhen, and Beijing results plus real-browser navigation.
