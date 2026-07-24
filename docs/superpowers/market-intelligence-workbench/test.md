# Verification Report

Date: 2026-07-19
Branch: `codex/analyst-workflow-v2`
Local verification URL: `http://127.0.0.1:8765`

## 2026-07-23 Market Summary Payload

- Added a response-contract regression test proving `/api/v1/market` omits the internal `snapshot.equities` universe while preserving metadata, indices, sectors, and analysis.
- The focused test failed against the old full-snapshot response, then passed after the explicit summary projection was added.
- Local production response size fell from the observed public baseline of 1,408,848 bytes to 9,666 bytes, a 99.3% reduction.
- `make verify` passed with 63 backend tests, 16 frontend tests, a production build, and live data covering 5,529 equities, 6 indices, and 100 sectors.

## Automated Gates

`make verify` passed the complete operator gate:

| Gate | Result |
| --- | --- |
| Ruff | Passed, no findings |
| mypy strict | Passed, 14 source files |
| Backend pytest | Passed, 28 tests |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 5 tests across 4 files |
| Vite production build | Passed, 1,650 modules transformed |
| Live data | Passed: 5,527 equities, 100.0% core-field coverage, 6 indices, 49 sectors |

Focused TDD checks run during V2 implementation:

```text
pnpm test --run src/features/stocks/StockLabPage.test.tsx
uv run pytest -q tests/test_analysis.py -k 'presets_are_distinct or risk_off_penalty'
uv run pytest -q tests/test_analysis.py -k 'multiple_visible_factors or high_volatility'
```

The focused tests were observed failing for the intended missing behavior before implementation, then passed after the corresponding implementation.

## Browser Workflow

The production build was served by FastAPI and tested in a real browser.

| Scenario | Result |
| --- | --- |
| Today route | Displayed market temperature 5, defensive regime, 25% research-risk reference, 70% evidence coverage, and linked next actions |
| Market route | Displayed real breadth, index, and sector evidence with weights; expanded 12 sectors to all 49 on demand |
| Trend strategy | Scanned 5,527 stocks; 151 passed; top result `星网锐捷` showed base 95, context penalty 15, final 80, and 50% evidence coverage |
| Unsupported strategies | Capital and sector strategies showed explicit unavailable explanations and rendered no fabricated candidate cards; sector-name-only input is regression-tested as insufficient without strength evidence |
| Oversold strategy | Returned a distinct candidate set headed by `特变电工`; copy identifies it as a daily observation proxy |
| Stock Lab | Loaded `SH.600519`, 180 bars, close/MA5/MA20/MA60, seven score factors, and 70% evidence coverage |
| Add to watchlist | Accepted an edited thesis and invalidation, then showed both `观察中 · 编辑记录` and a persistent success confirmation |
| Watchlist persistence | Updated status, thesis, and invalidation; showed `已保存` and linked back to the dossier |
| Data Center | Displayed observation/fetch timestamps, delayed freshness, 100% coverage, and a successful manual-refresh timestamp |
| Desktop layout | Passed at 1,280 CSS pixels with no horizontal overflow |
| Desktop workflow | Today, Opportunities, Stock Lab, and Watchlist passed at 1440 x 900, 1536 x 900, and 1920 x 1080 with no horizontal overflow |
| Browser logs | No warning or error entries after the complete workflow |

## Data Assertions

- The market observation timestamp was `2026-07-17 15:00:00`, the latest completed A-share session before the weekend test date.
- Sina supplied the 5,527-stock universe and 49 industry snapshots.
- Tencent supplied the six required core indices and stock history.
- Missing sector capital flow is presented as unavailable, never as a fabricated zero.
- Market factors expose the evidence counts used by the deterministic score; unavailable factors are excluded and available weights are renormalized.
- The defensive regime applies a visible 15-point penalty to opportunity scores; cautious mode applies 8 points.
- Stock stance starts at 50 and is reproducible from the displayed factor impacts rather than one moving-average threshold.

## Residual Risks

- Public market endpoints and their terms can change without notice; production or commercial use still needs a licensing review.
- Previous-market-day selection handles weekends but does not yet use an official exchange holiday calendar.
- Semantic research enrichment was not exercised because the optional endpoint and API key are not configured.
- Stock-level sector mapping and capital-flow coverage are not available in the current normalized universe; dependent strategies stop with an explicit reason.
- Oversold observation is a single-day proxy, not confirmation of a multi-day reversal.
- FastAPI TestClient emits one third-party Starlette/httpx deprecation warning; it does not affect runtime behavior.

## Regression Sweep After Market Events, Holdings, and Auto Refresh

Date: 2026-07-20
Scope: merge latest `new_ts` logic into StockTs while preserving the desktop-only public deployment contract.

Expected final gate:

```text
make verify
```

Coverage added in this merge:

- Backend event analysis infers readable sector names from market news and avoids leaking raw `BK` codes into summaries.
- `/api/v1/market-events` returns classified events, clusters, impacts, and next actions.
- Opportunity presets expose diagnostics, candidate dimensions, thesis, invalidation, and next actions.
- Stock dossiers expose direct advice, analysis dimensions, horizontal comparison, vertical comparison, and clean conclusions.
- Holdings support create, edit, delete, local persistence, position analysis, rebalance hints, and risk flags.
- Production service explicitly enables `MARKETDESK_AUTO_REFRESH_INTERVAL_SECONDS=7200`.
- Frontend regression covers Today event radar, Market event verification, Opportunities decision cards, Stock advice/comparison, Watchlist journal, Holdings editor, and Data Center auto-refresh status.

Desktop boundary:

- Browser code remains API-only through `/api/v1/*`.
- Public browser routes remain a desktop workbench: no device-scaling metadata, no drawer navigation, no bottom bar, and no narrow-screen CSS.

## 2026-07-24 Full-Market Browser

The compact `/api/v1/market` contract remains unchanged. A dedicated bounded endpoint now exposes the cached full A-share universe through search, numeric ranking, and one-based server pagination.

TDD evidence:

- The backend route test first failed because `/api/v1/equities` fell through to the SPA HTML response, then passed after the typed endpoint and service page contract were implemented.
- The Market page interaction test first failed because `全市场行情` did not exist, then passed after the isolated quote browser was mounted.
- A focused honesty regression first failed because a missing `change_pct` cell received the `up` class, then passed after missing values were rendered without directional color.

Final local gate:

| Gate | Result |
| --- | --- |
| Ruff | Passed, no findings |
| mypy | Passed, 19 source files |
| Backend pytest | Passed, 64 tests |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 17 tests |
| Vite production build | Passed, 1,652 modules transformed |
| Live data | Passed: 5,530 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

Contract assertions cover Chinese-name and code search, both numeric sort directions, missing values last, bounded page size, and an empty out-of-range page with the true total. Frontend interaction coverage includes ranking, explicit search submission, page navigation, Stock Lab links, and neutral styling for missing change evidence.

The in-app browser could not establish a stable connection to the local development server even though terminal health and API checks were normal. Public browser interaction and production API smoke checks are therefore required after deployment and will be recorded separately.

### Production Smoke

Release `20260724-114030-8d3fee6` was deployed to `stock.jiewat-kaka-fj.com` and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health | `/healthz` returned `status=ok`; systemd service active |
| Full-market default | 5,530 total equities; exactly 25 items returned |
| Search | `q=茅台` returned `SH.600519` |
| Pagination | Page 1 and page 2 had different first symbols; browser reached page 2 of 222 |
| Sorting | Amount accepted both directions; missing values remained last on the final page |
| Compact market summary | 9,960 bytes; snapshot keys remained `meta`, `indices`, and `sectors` |
| Persistent data | 7 holdings and 2 watchlist records remained available after release switch |

Real Chrome at 1,440 x 900 rendered the panel, searched to the single `贵州茅台` result, switched to change-percentage ranking, moved to the second page, and exposed Stock Lab links. The page had no document-level horizontal overflow and emitted no browser console or page errors.

## 2026-07-24 Full-Market Navigation

The full-market browser now filters the cached universe by Shanghai, Shenzhen, or Beijing exchange before applying the existing search, deterministic sort, and bounded page slice. The client adds 25/50-row selection, first/last controls, a visible result range, and direct page entry with out-of-range values clamped to the nearest valid page.

TDD evidence:

- The backend focused test failed on the missing `exchange` response key, then passed after the typed route, model, and service filter were connected.
- The frontend focused test failed because the `交易所` control did not exist, then passed after navigation state and controls were implemented.
- The first GREEN attempt exposed native number-input validation blocking an out-of-range jump before application clamping could run. The jump form now bypasses native blocking and the regression proves `999` resolves to the last valid page.

Final local gate:

| Gate | Result |
| --- | --- |
| Ruff | Passed, no findings |
| mypy | Passed, 19 source files |
| Backend pytest | Passed, 64 tests |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 18 tests |
| Vite production build | Passed, 1,652 modules transformed |
| Live data | Passed: 5,530 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

The focused interaction suite verifies exchange reset, 25/50 page-size reset, bounded direct jump, first/last controls, query parameters, and synchronized page input. Production must still confirm that the live normalized universe contains non-empty `SH.`, `SZ.`, and `BJ.` partitions.

### Production Smoke

Release `20260724-120226-72e4c59` was deployed and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Full universe | 5,530 equities |
| Shanghai | 2,308 equities; returned symbols use `SH.` |
| Shenzhen | 2,892 equities; returned symbols use `SZ.` |
| Beijing | 330 equities; returned symbols use `BJ.` and page 2 is non-empty |
| Combined filter | `exchange=sh&q=600519` returned `贵州茅台` |
| Validation | Unsupported `exchange=hk` returned HTTP 422 |
| Page size | 50-row response returned exactly 50 rows |
| Persistent data | 7 holdings and 2 watchlist records remained available |

Real Chrome at 1,440 x 900 selected Beijing listings, switched from 25 rows/14 pages to 50 rows/7 pages, opened the last page at rows 301–330, returned to the first page, and clamped page `999` to page 7. Searching `920211` returned `新睿电子` with a Stock Lab link. The page had no document-level horizontal overflow and emitted no console or page errors.

## 2026-07-24 Advanced Full-Market Filters and Saved Views

The full-market endpoint now combines industry, change percentage, amount, turnover, market-cap, and core-data-completeness filters before deterministic sorting and pagination. The Market page stores active research conditions in the hash URL and lets the current account create, apply, and delete validated reusable views without storing a stale page number.

TDD evidence:

- Six backend tests first failed on ignored query parameters, missing range validation, and absent saved-view routes; they passed after service filtering, Pydantic contracts, SQLite persistence, and account-scoped APIs were connected.
- The store test first failed because `EquityViewFilters` and view CRUD did not exist, then passed with cross-account delete isolation.
- Two Market interaction tests first failed because advanced controls and saved-view actions were absent, then passed with URL restoration, yuan-to-100-million-yuan conversion, and create/apply/delete coverage.
- A whitespace-only view-name regression first returned HTTP 201, then returned HTTP 422 after server-side normalization.

Final local gate before release:

| Gate | Result |
| --- | --- |
| Ruff | Passed, no findings |
| mypy | Passed, 19 source files |
| Backend pytest | Passed, 71 tests |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 20 tests |
| Vite production build | Passed, 1,652 modules transformed |
| Live data | Passed: 5,530 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

Real Chromium at 1,440 x 1,000 restored `白酒Ⅱ`, minimum amount `10` hundred-million-yuan units (CNY 1 billion), maximum turnover `5%`, and complete-data mode from the URL, returning one real row with no document overflow. A temporary saved view was created and deleted through the live local API. At 390 x 844 the first run exposed a 920px shell overflow; after the responsive-shell fix, the main area measured 390px, the advanced panel 360px, document overflow was false, and the console reported zero errors or warnings.
