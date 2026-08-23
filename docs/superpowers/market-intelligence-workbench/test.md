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

### Production Smoke

Release `20260724-132150-ab91a9b` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health and service | `/healthz` returned `status=ok`; systemd service active |
| Combined advanced filter | `白酒Ⅱ`, change >= 0%, amount >= CNY 1 billion, turnover <= 5%, complete data returned only `SH.600519` |
| Industry facet | 128 real non-empty equity industries returned |
| Saved-view persistence | Temporary view created in the production SQLite store and deleted with HTTP 204 |
| Desktop browser | Restored industry and amount from URL, showed one row, no document overflow |
| Mobile browser | 390px main, 360px advanced panel, no document overflow |
| Browser runtime | Zero console errors or warnings |

## 2026-07-24 Personal Data Authentication Boundary

Production diagnosis showed that storage isolation was already correct: user 1 owned 7 holdings, user 2 owned 0, and there were no orphan holdings. A temporary authenticated account received 0 holdings, while the same request without a bearer token received user 1's 7 holdings. The root cause was the API's missing-authorization fallback to the default owner, not duplicated database rows or a broken `user_id` query.

The fallback is removed. `/auth/me`, preferences, holdings, watchlists, and saved equity views now return HTTP 401 without a valid bearer token. Holdings and watchlist pages show an explicit login boundary instead of an empty or shared portfolio, and failed authentication never falls back to another account.

TDD evidence:

- The backend regression first received HTTP 200 from `/auth/me` without credentials, then passed after all personal GET endpoints returned HTTP 401 while `/api/v1/market` remained public.
- The frontend regression first rendered a zero-value portfolio and an enabled add form after a holdings 401, then passed after the page rendered `请先登录后查看个人持仓` and no personal list.
- Existing personal API tests now authenticate their fixture client explicitly; the two-user isolation test still proves different quantities for the same symbol.

Final local gate before release:

| Gate | Result |
| --- | --- |
| Ruff | Passed, no findings |
| mypy | Passed, 19 source files |
| Backend pytest | Passed, 72 tests |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 21 tests |
| Vite production build | Passed, 1,652 modules transformed |
| Live data | Passed: 5,530 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

Real Chromium opened the local holdings route without credentials and showed only the login boundary. Registering a temporary account on the same page removed the gate and rendered an empty zero-row portfolio for that account rather than the default owner's holdings.

### Production Smoke

Release `20260724-203821-9e7277f` was deployed and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Anonymous personal APIs | `/auth/me`, preferences, holdings, watchlist, and equity views all returned HTTP 401 |
| Account A | Created one temporary `SH.600519` holding and received exactly one holding |
| Account B | Received zero holdings while account A still owned one |
| Data preservation | Temporary accounts and rows removed; owner retained all 7 holdings |
| Browser boundary | Logged-out Holdings page showed the login requirement, zero holding rows, and the register/login action |

This proves the deployed system distinguishes `unauthenticated`, `account A`, `account B`, and the existing owner instead of routing them to one shared portfolio.

## Stock Analysis Engine V3 — 2026-07-25

### Open-source method review

The implementation was informed by primary-source review of Qlib, vn.py, Backtrader, QuantConnect LEAN, and FinRL. The adopted boundary is deterministic and dependency-free: indicator math is isolated, risk management is separate from signal generation, and historical validation is descriptive rather than a promise of future performance. Full notes are in `docs/tech-specs/2026-07-25-open-source-stock-analysis-review.md`.

### TDD evidence

- Indicator tests failed first because `marketdesk.analysis.indicators` did not exist, then passed after EMA, MACD, ATR, Bollinger, and maximum-drawdown implementations were added.
- Stock analysis tests failed first on missing technical fields, factors, confluence, and validation, then passed after the V3 response contract and deterministic logic were added.
- A full backend run exposed MACD floating-point noise (`-0.000`) as a false negative signal. A dedicated regression test failed, then passed after near-zero histogram values were classified as neutral.
- ATR guidance tests failed against structural-only stop and target copy, then passed after adding two-ATR risk lines, three-ATR review targets, and volatility-aware trial-size caps.
- The Stock Lab test failed before the historical validation panel existed, then passed with the compact panel in the original section order.
- The anonymous Stock Lab test failed while the page still requested the private watchlist, then passed after the query was disabled without an access token and the action was labelled `登录后加入跟踪`.

### Repository verification

`make verify` passed before final documentation with:

- backend lint and types clean across 20 source files;
- 83 backend tests passed;
- 22 frontend tests passed;
- production frontend build completed;
- live-data gate returned 5,530 equities, six indices, 100 sectors, and 100% equity coverage.

The final gate passed again after this record was updated: 83 backend tests and 23 frontend tests passed, the production build completed, and the live-data gate remained at 5,530 equities with 100% coverage.

### Real-browser acceptance

The production build was served through FastAPI and checked with Chrome against `SH.600519`.

| Check | Result |
| --- | --- |
| V3 evidence | MACD, ATR, Bollinger/drawdown factors and signal confluence rendered from the stock API |
| Historical validation | Rendered between future trend and horizontal/vertical comparison; stated sample count, 20-day result distribution, overlapping-sample caveat, and no-score boundary |
| Desktop 1440 x 900 | `scrollWidth=1440`, no horizontal overflow; existing section order preserved |
| Mobile 390 x 844 before review fix | `scrollWidth=603`; fixed-grid Stock Lab sections caused overflow |
| Mobile 390 x 844 after review fix | `scrollWidth=390`, no horizontal overflow; advice, forecast, comparison, evidence, and validation grids collapse cleanly |
| Anonymous account boundary | No `/api/v1/watchlist` request, disabled `登录后加入跟踪` action, zero browser console errors |

Generated screenshots remain under the ignored local `.run/` directory and are not committed.

### Production smoke

Release `20260725-120422-d576575` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health and service | Public `/healthz` returned `status=ok`; systemd service active |
| V3 stock contract | `SH.600519` returned `technical.macd_histogram`, `technical.atr_pct`, and a populated `signal_validation` object |
| New score evidence | The live response included `macd_momentum`, `atr_risk`, `bollinger_position`, and `drawdown_risk` |
| Historical validation | 36 rolling samples; 19% positive rate, -3.19% average return, and -10.04% worst return, with the overlap and no-score caveats preserved |
| Anonymous personal APIs | Holdings, watchlist, preferences, and equity views all returned HTTP 401 |
| Desktop browser | 1,440px viewport and 1,440px document width; historical validation visible; zero page errors |
| Mobile browser | 390px viewport and 390px document width; future trend, historical validation, and comparison remained in order; zero page errors |
| Anonymous Stock Lab | Only public stock and search APIs were requested; the private tracking action stayed disabled |
| Persistent data boundary | `/opt/aster-market/data` remained outside the release and `/opt/aster-market/current/data` was absent |

The rollback tag `release-2026-07-25` remains fixed at `b1c7a80`. Rolling back this application release must continue to leave `/opt/aster-market/data` untouched.

## Application Authentication Gate — 2026-07-25

The application shell no longer doubles as the login surface. Anonymous visitors receive a standalone login/register page, and the React feature tree is not mounted until a stored bearer token is validated. The backend independently protects every `/api/v1/*` business route so the same boundary cannot be bypassed with a direct request.

### TDD evidence

- The backend regression first failed because anonymous `/api/v1/market` returned HTTP 200. It passed after one application-wide middleware restricted all market, analysis, refresh, and personal routes while leaving only registration and login anonymous.
- The frontend regression first failed because the sidebar, main navigation, refresh control, and Today query mounted without a token. It passed after the root session gate rendered the standalone authentication page instead.
- Session regressions cover registration, bearer-authenticated business requests, valid stored-session restoration, expired-token cleanup, immediate logout, and query-cache clearing.

### Local browser acceptance

| Check | Result |
| --- | --- |
| Anonymous desktop | 1,440px viewport and 1,440px document width; standalone login visible; no main navigation or market conclusion |
| Anonymous mobile | 390px viewport and 390px document width; standalone login visible; no main navigation or full-market content |
| Anonymous network | Zero `/api/v1/*` requests before login on both direct Stock Lab and Market URLs |
| Registration | Created an isolated local QA account, then mounted the existing shell and loaded preferences, Today, and market events |
| Logout | Immediately removed the shell, navigation, and market content and returned to the standalone login page |
| Browser runtime | Zero page errors before login, after registration, and after logout |

### Production smoke

Release `20260725-122901-4f16a16` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health and service | Public `/healthz` returned `status=ok`; systemd service active |
| Anonymous research APIs | Market, Today, equities, opportunities, stock dossier, search, and data status all returned HTTP 401 |
| Anonymous write and personal APIs | Refresh, holdings, watchlist, preferences, and equity views all returned HTTP 401 |
| Authentication entry points | Empty registration and login payloads reached request validation and returned HTTP 422 rather than the application gate's 401 |
| Desktop browser | Direct Stock Lab URL rendered only `登录 Market Desk`; 1,440px viewport and document width; zero business API requests and page errors |
| Mobile browser | Direct Market URL rendered only `登录 Market Desk`; 390px viewport and document width; zero business API requests and page errors |
| Persistent data boundary | Data-directory inode `1204950` was unchanged; the release contained no `data` path |

The rollback tag `release-2026-07-25` remains the application rollback anchor at `b1c7a80`; `/opt/aster-market/data` remains outside application rollback scope.

## Ask Stock Workbench — 2026-07-25

The authenticated workbench now includes a separate `问股` route without changing the existing module layouts. Questions containing one A-share name or six-digit code reuse the current full-market snapshot and deterministic Stock Lab dossier. Broad natural-language screens use the optional semantic provider and fail explicitly when it is not configured.

### TDD evidence

- The analysis test first failed because `marketdesk.analysis.ask_stock` did not exist, then passed with code/name resolution, ambiguity protection, five deterministic intents, and bounded evidence composition.
- The provider test first failed on missing `normalize_stock_screen`, then passed with code/name-first columns, scalar-only cells, and 20-row/12-column limits.
- The semantic request test first failed on missing `query_stocks`, then passed with server-side bearer authentication and a maximum result limit of 20.
- The API tests first received HTTP 405 because `/api/v1/ask-stock` was absent, then passed for authentication, validation, local analysis, ambiguity, semantic fallback, and HTTP 503 degradation.
- The page test first failed because `AskStockPage` did not exist, then passed for suggested questions, named-stock evidence, semantic tables, and preserved input on an unavailable response.
- The route test first logged `No routes matched location "/ask"`, then passed after the route and sidebar entry were added behind `SessionGate`.

### Repository verification

`make verify` passed with:

| Gate | Result |
| --- | --- |
| Ruff | Passed, no findings |
| mypy | Passed, 21 source files |
| Backend pytest | Passed, 106 tests |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 28 tests in 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,530 equities, 100.0% coverage, 6 indices, 100 sectors |

### Production-build browser acceptance

Chrome loaded the FastAPI-served production bundle at the direct `#/ask` URL.

| Check | Result |
| --- | --- |
| Anonymous boundary | Standalone login rendered; zero business API requests before registration |
| Authenticated route | `问股` appeared in the existing sidebar and remained inside the authenticated shell |
| Named-stock question | `贵州茅台现在主要风险是什么` returned `SH.600519`, the local deterministic source, market observation time, evidence, risks, next actions, and disclaimer |
| Provider unavailable | `低估值白酒股` retained the typed question and rendered the explicit HTTP 503 configuration message |
| Desktop 1280 px | Document width remained 1,280 px with zero console errors on the successful named-stock path |
| Mobile 390 px | Document and viewport widths both remained 390 px; composer, answer, and three evidence sections stacked without document overflow |

The unavailable semantic request produces the browser's expected failed-resource console entry for HTTP 503; the application renders that response as a controlled error state. No credential, Cookie, or provider payload is exposed to browser code.

### Production smoke

Release `20260725-135335-cdf90b4` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health and service | Public `/healthz` returned `status=ok`; systemd service active |
| Anonymous Ask Stock | `POST /api/v1/ask-stock` without a bearer token returned HTTP 401 with `authentication required` |
| Authenticated Ask Stock | A temporary smoke account registered and asked `贵州茅台现在主要风险是什么`; response returned HTTP 200, `kind=stock_analysis`, `symbol=SH.600519`, source `本地行情快照 + 确定性分析`, 4 evidence items, and 3 risks |
| Semantic fallback | `低估值白酒股` returned the controlled HTTP 503 provider-unavailable message because the production Wencai semantic endpoint is not configured |
| Session cleanup | The temporary smoke session was logged out and all `codex-smoke-%@marketdesk.local` users were removed from the production database |
| Persistent data boundary | `/opt/aster-market/data` remained outside the release; `/opt/aster-market/current/data` was absent |

The rollback tag `release-2026-07-25` remains fixed at `b1c7a80`; this Ask Stock deployment does not change the rollback data boundary.

## Ask Stock Conversational UI — 2026-07-25

The Ask Stock page now behaves as a multi-turn conversation instead of a single-submit answer card. The page keeps the current answer history in a message thread, displays user and assistant turns, keeps suggested prompts available, and adds a clear-thread action. Follow-up questions such as `那估值呢` carry the latest named-stock context into the deterministic Ask Stock endpoint while preserving the user's original wording in the chat.

### Regression evidence

| Check | Result |
| --- | --- |
| Suggested prompt | Clicking `贵州茅台现在主要风险是什么` appends a user message and a structured assistant answer |
| Multi-turn context | After the first `SH.600519` answer, submitting `那估值呢` calls the API as `贵州茅台 那估值呢` and renders `沿用上文：贵州茅台 SH.600519` |
| Semantic table | Broad screening responses still render bounded rows and columns inside the chat thread |
| Provider unavailable | HTTP 503 details render as an inline error message and the typed question stays in the composer |
| App route | The authenticated `#/ask` route still mounts behind the application shell and highlights `问股` |

### Local browser acceptance

Chrome loaded the FastAPI-served production bundle at `http://127.0.0.1:8765/#/ask` with a temporary local account.

| Check | Result |
| --- | --- |
| Desktop chat | 1,280px viewport and 1,280px document width; two user turns plus two assistant turns rendered |
| Follow-up | `贵州茅台现在主要风险是什么` then `那估值呢` returned two HTTP 200 Ask Stock answers and displayed the carried-stock marker |
| Mobile chat | 390px viewport and 390px document width after adding the missing viewport meta tag |
| Cleanup | Temporary `local-ask-chat-%@marketdesk.local` users were removed from the local database |

### Production smoke

Release `20260725-163418-776c1a4` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| HTML shell | Public `/` returned the production HTML with `meta name="viewport"` |
| Anonymous Ask Stock | `POST /api/v1/ask-stock` without a bearer token returned HTTP 401 |
| Authenticated first turn | Temporary smoke account asked `贵州茅台现在主要风险是什么`; response returned HTTP 200, `kind=stock_analysis`, `symbol=SH.600519`, `intent=risk` |
| Authenticated follow-up | The carried-context request `贵州茅台 那估值呢` returned HTTP 200, `kind=stock_analysis`, `symbol=SH.600519`, `intent=valuation` |
| Service and data boundary | `/opt/aster-market/current` pointed to the new release, `stock-ts.service` was active, `/opt/aster-market/current/data` was absent, and `/opt/aster-market/data` remained external |
| Cleanup | Temporary `codex-chat-smoke-%@marketdesk.local` users were removed from the production database |

## 2026-07-25 Ask Stock Conversation Refinement

The Ask Stock workbench now keeps the current tab's authenticated conversation thread, supports quick follow-up prompts after each stock answer, retries failed turns inline, submits with Enter while preserving Shift+Enter for drafting, and links stock answers directly back to Stock Lab.

Analysis refinement:

- Local stock resolution now accepts unique short aliases such as `茅台主要风险` for `SH.600519` while preserving the existing one-stock-only boundary for mixed questions.
- Ambiguous local questions still return the explicit `一次只问一只股票` validation path instead of blending multiple dossiers.
- Broad semantic-screening questions still use the optional provider layer when no unique local stock is identified.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused backend Ask tests | Passed: 19 ask-stock tests |
| Focused frontend Ask tests | Passed: 6 tests |
| Frontend typecheck | Passed |
| Full frontend Vitest | Passed: 31 tests across 8 files |
| Production build | Passed: 1,653 modules transformed |
| `make verify` | Passed: 106 backend tests, 31 frontend tests, live data 5,530 equities, 6 indices, 100 sectors |

Real Chrome at 1,280 x 900 opened Ask Stock with an authenticated token, asked `贵州茅台现在主要风险是什么`, used the inline `继续问估值` follow-up, refreshed the page, and restored the thread plus active stock context. The Stock Lab link resolved to `#/stocks?symbol=SH.600519`. Desktop and 390px mobile viewports both measured no document-level horizontal overflow.


### Production smoke

Release `20260725-164925-9758197` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| HTML shell | Public `/` returned the production HTML with viewport metadata |
| Anonymous Ask Stock | `POST /api/v1/ask-stock` without a bearer token returned HTTP 401 |
| Alias stock question | Temporary smoke account asked `茅台主要风险`; response returned HTTP 200, `kind=stock_analysis`, `symbol=SH.600519`, `intent=risk` |
| Authenticated follow-up | The carried-context request `贵州茅台 那估值呢` returned HTTP 200, `kind=stock_analysis`, `symbol=SH.600519`, `intent=valuation` |
| Browser conversation | Real Chrome at 1,280 x 900 asked the first question, clicked `继续问估值`, refreshed, and restored active context `贵州茅台 SH.600519` |
| Responsive boundary | Real Chrome measured 1,280px desktop width and 390px mobile width with matching document scroll width |
| Stock Lab link | Ask answer link resolved to `#/stocks?symbol=SH.600519` |
| Service and data boundary | `/opt/aster-market/current` pointed to the new release, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-ask-refine-%@marketdesk.local` users were removed from the production database |

## 2026-07-25 Ask Stock Decision Metrics

The Ask Stock API now returns a compact `metrics` strip for both deterministic stock answers and semantic-screening results. Stock answers expose the existing deterministic dossier score, suggested action, evidence coverage, advice confidence, latest price, and change percentage. Semantic-screening answers expose candidate count and enhancement source, while recognized stock-code cells link directly to Stock Lab.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused backend Ask tests | Passed: 19 ask-stock tests |
| Focused frontend Ask tests | Passed: 6 tests |
| Backend mypy | Passed: 21 source files |
| Frontend typecheck | Passed |
| `make verify` | Passed: 106 backend tests, 31 frontend tests, production build, live data 5,530 equities, 6 indices, 100 sectors |

Real Chrome at 1,280 x 900 rendered the Ask Stock metric strip for `贵州茅台现在主要风险是什么`: `综合分72`, `建议动作持有观察`, `证据覆盖90%`, `置信度82%`, `最新价1297.41`, and `涨跌幅+0.42%`. The Stock Lab link resolved to `#/stocks?symbol=SH.600519`; desktop and 390px mobile viewports had matching document scroll width.


### Production smoke

Release `20260725-170200-df69673` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| HTML shell | Public `/` returned the production HTML with viewport metadata |
| Anonymous Ask Stock | `POST /api/v1/ask-stock` without a bearer token returned HTTP 401 |
| Metric API | Temporary smoke account asked `茅台主要风险`; response returned `symbol=SH.600519`, `intent=risk`, and metrics `综合分72`, `建议动作持有观察`, `证据覆盖90%` |
| Browser metrics | Real Chrome at 1,280 x 900 rendered `综合分72`, `建议动作持有观察`, `证据覆盖90%`, `置信度82%`, `最新价1297.41`, and `涨跌幅+0.42%` |
| Responsive boundary | Real Chrome measured 1,280px desktop width and 390px mobile width with matching document scroll width; mobile metric grid collapsed to two columns |
| Stock Lab link | Ask answer link resolved to `#/stocks?symbol=SH.600519` |
| Service and data boundary | `/opt/aster-market/current` pointed to the new release, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-ask-metric-%@marketdesk.local` users were removed from the production database |

## 2026-07-25 Ask Stock Holding-Aware Refactor

Ask Stock was refactored into three explicit answer paths: deterministic single-stock analysis, authenticated holding-context analysis, and portfolio-level analysis. The API now exposes `holding_context` for owned stocks and `factors` for score transparency; portfolio questions such as `我的持仓里风险最大的是哪个` return an account-scoped ranked table without using default-owner fallback or another user's holdings.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused backend Ask tests | Passed: 21 ask-stock tests, including current-user holding context and cross-account portfolio isolation |
| Focused frontend Ask tests | Passed: 8 tests, including holding context, factor disclosure, and portfolio rows |
| `make verify` | Passed: 108 backend tests, 33 frontend tests, production build, live data 5,530 equities, 6 indices, 100 sectors |

Local API smoke created two temporary accounts. Account A created a `SH.600519` holding and received `portfolio_analysis` with `持仓数量=1`, a `SH.600519` portfolio row, and stock-level `holding_context.owned=true`. Account B asked the same portfolio question and received `持仓数量=0` with no rows. Real Chrome at 1,280 x 900 rendered the portfolio table, personal holding context, and factor disclosure; after reload at 390px mobile width, the restored conversation had no document-level horizontal overflow. Temporary local users were removed from `data/marketdesk.db`.


### Production smoke

Release `20260725-171525-0d2f3f9` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| HTML shell | Public `/` returned the production HTML with viewport metadata |
| Anonymous Ask Stock | `POST /api/v1/ask-stock` without a bearer token returned HTTP 401 |
| Account A portfolio | Temporary Account A created one `SH.600519` holding; `我的持仓里风险最大的是哪个` returned `kind=portfolio_analysis`, `持仓数量=1`, and a `SH.600519` row |
| Account B isolation | Temporary Account B asked the same portfolio question and received `持仓数量=0` with no rows |
| Holding-aware stock answer | Account A asked `我持有的贵州茅台要减仓吗`; response returned `holding_context.owned=true`, `持仓盈亏=-23.68%`, and 11 score factors |
| Browser workflow | Real Chrome at 1,280 x 900 rendered the portfolio table, personal holding context, and factor disclosure |
| Responsive boundary | Real Chrome measured 1,280px desktop width and 390px mobile width with matching document scroll width after conversation restore |
| Service and data boundary | `/opt/aster-market/current` pointed to the new release, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-ask-refactor-%@marketdesk.local` users and holdings were removed from the production database |

## 2026-07-25 Ask Stock Portfolio Diagnostics

The Ask Stock portfolio path now handles portfolio-diagnostic questions even when the question names a specific stock, such as `我的持仓里贵州茅台占比是不是太高`. This prevents a portfolio allocation question from being downgraded into ordinary single-stock analysis. The response keeps account scoping and adds concentration evidence: largest single-position weight, highest sector concentration, target-weight drift, missing invalidation records, and triggered risk flags.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused backend Ask tests | Passed: 23 ask-stock tests, including named-stock portfolio diagnostics and cross-account isolation |
| Focused frontend Ask tests | Passed: 8 tests, including portfolio concentration metrics, target-weight columns, and factor disclosure |
| Backend mypy and ruff | Passed: 21 source files, no lint findings |
| `make verify` | Passed: 110 backend tests, 33 frontend tests, production build, live data 5,530 equities, 6 indices, 100 sectors |

Local API regression created Account A with three holdings across `SH.600519`, `SZ.000001`, and `BJ.430047`; `我的持仓里贵州茅台占比是不是太高` returned `kind=portfolio_analysis`, named `SH.600519` in the answer, exposed metrics for `最大单票` and `行业集中`, and returned rows with `行业`, `目标仓位`, and `偏离`. Account B asked the same question and received `持仓数量=0` with no rows, proving the diagnostic still does not fall back to default-owner data.

## 2026-07-26 Ask Stock Rebalance Plan

Ask Stock now treats questions such as `帮我生成调仓计划`, `组合怎么调仓`, and `仓位调整` as account-scoped portfolio questions even when no stock name is present. The response uses existing holding analysis to build a deterministic rebalance plan with target-weight drift, adjustment value, suggested shares, priority, and guardrail next actions.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused backend Ask tests | Passed: 24 ask-stock tests, including rebalance intent detection, account-scoped plan rows, and empty-account isolation |
| Focused frontend Ask tests | Passed: 9 tests, including the new quick prompt, rebalance metrics, suggested-share column, and priority cells |
| Backend ruff and mypy | Passed: 21 source files, no lint findings |
| Frontend typecheck | Passed |
| `make verify` | Passed: 111 backend tests, 34 frontend tests, production build, live data 5,530 equities, 6 indices, 100 sectors |

Local API regression created Account A with three holdings and asked `帮我生成调仓计划`; the API returned `kind=portfolio_analysis`, metrics `需调仓` and `净调整`, columns `偏离金额`, `建议股数`, and `优先级`, a high-priority first row, and a guardrail reminding the user not to trade mechanically from the table. Account B asked the same question and received `持仓数量=0` with no rows.

### Production smoke

Release `20260726-134428-fb7d4c8` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health and auth boundary | `/healthz` returned HTTP 200; anonymous `POST /api/v1/ask-stock` returned HTTP 401 |
| Account A rebalance plan | Temporary Account A created three holdings; `帮我生成调仓计划` returned `kind=portfolio_analysis`, metrics `需调仓`, `净调整`, `最大单票`, and a first row with `建议股数` and `优先级=高` |
| Account B isolation | Temporary Account B asked the same rebalance question and received `持仓数量=0` with no rows |
| Browser workflow | Real Chrome at 1,280 x 900 rendered the Ask Stock rebalance plan, `建议股数`, `调仓执行量`, and the guardrail `不按表格机械交易` |
| Responsive boundary | Real Chrome measured 1,280px desktop width and 390px mobile width with matching document scroll width |
| Service and data boundary | `/opt/aster-market/current` pointed to the new release, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-rebalance-%@marketdesk.local` and `codex-rebalance-ui-%@marketdesk.local` users and holdings were removed from the production database |

## 2026-07-26 Ask Stock Follow-up Context And Neutral Provider Copy

Ask Stock now carries the previous single-stock context for natural follow-up questions such as `你觉得多少合理`, `目标价多少`, `还能买吗`, and `要不要卖`, while still not carrying context for portfolio questions or broad screening-style queries such as `低估值白酒股`. User-facing copy no longer exposes the optional semantic provider name; the page and API use `条件选股增强` instead.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused backend Ask tests | Passed: 10 API ask-stock tests, including neutral provider success and unavailable messages |
| Focused frontend Ask tests | Passed: 10 tests, including `贵州茅台` followed by `你觉得多少合理` carrying `SH.600519` context |
| `make verify` | Passed: 111 backend tests, 35 frontend tests, production build, live data 5,530 equities, 6 indices, 100 sectors |

Regression details:

- The frontend request sequence for the natural follow-up is now `贵州茅台现在主要风险是什么` then `贵州茅台 你觉得多少合理`.
- Error and success states assert that `问财` is absent from rendered Ask Stock UI.

### Production smoke

Release `20260726-204031-2b6e17f` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Neutral unavailable copy | Authenticated `低估值白酒股` returned HTTP 503 with `条件选股增强暂不可用；你也可以在问题中包含一个 A 股股票名称或代码继续分析。` |
| Follow-up context | Real Chrome asked `贵州茅台现在主要风险是什么`, then `你觉得多少合理`; the captured API requests were `贵州茅台现在主要风险是什么` and `贵州茅台 你觉得多少合理` |
| Provider branding | Real Chrome body text did not contain `问财`, `WenCai`, or `iWenCai` after the follow-up workflow |
| Responsive boundary | Real Chrome measured 1,280px desktop width and 390px mobile width with matching document scroll width |
| Service and data boundary | `/opt/aster-market/current` pointed to the new release, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-followup-%@marketdesk.local` users were removed from the production database |

## 2026-07-26 Refresh Timestamp Clarity

The top timestamp chip now separates `行情时间` from `更新`, using `observed_at` for the market session represented by the quotes and `fetched_at` for the latest successful local refresh. This avoids making a weekend or post-close snapshot look stale just because the latest market session remains the previous trading day's 15:00 close.

Verification evidence:

| Gate | Result |
| --- | --- |
| App shell timestamp test | Passed: the authenticated Today route renders both `行情时间` and `更新`, and a manual refresh changes the displayed update year to `2030` in the fixture |
| Data Center timestamp test | Passed: the audit grid uses `行情时间` and `更新时间`, and manual refresh status reports `更新时间` |
| `make verify` | Passed: 111 backend tests, 36 frontend tests, production build, live data 5,530 equities, 6 indices, 100 sectors |

### Production smoke

Release `20260726-205803-612b618` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Timestamp API boundary | Authenticated refresh returned HTTP 200; `observed_at=2026-07-24T07:00:00Z` stayed on the latest completed A-share session while `fetched_at=2026-07-26T13:04:50.432568Z` advanced to the latest refresh |
| Top timestamp chip | Real Chrome rendered `行情时间 2026/7/24 15:00:00` and `更新 2026/7/26 21:04:50` on both desktop and 390px mobile |
| Desktop layout | 1,280px viewport and document width both measured 1,280px |
| Mobile layout | 390px viewport and document width both measured 390px after constraining sidebar overflow and collapsing the Today risk rail |
| Browser runtime | Zero console warnings or page errors on the authenticated Today route |
| Service and data boundary | `/opt/aster-market/current` pointed to `/opt/aster-market/releases/20260726-205803-612b618`, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-refresh-time-%@marketdesk.local` and `codex-overflow-debug-%@marketdesk.local` users were removed from the production database |

## 2026-07-26 Ask Stock Qinglong Alias Disambiguation

Ask Stock no longer treats weak two-character suffix aliases such as `龙股` from ex-dividend names like `XD腾龙股` as reliable stock identifiers. A colloquial question such as `为什么是青龙股份` now resolves through the unique prefix alias `青龙` to `SZ.002457 青龙管业` instead of failing with `一次只问一只股票`.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused resolver regression | Passed: `青龙股份怎么样`, `为什么是青龙股份`, `青龙股份`, and `青龙` resolve to `SZ.002457 青龙管业` with the current local market snapshot |
| Focused backend Ask tests | Passed: 25 Ask Stock API/analysis tests, including the existing multi-stock rejection and the new Qinglong colloquial-name acceptance |
| `make verify` | Passed: 112 backend tests, 36 frontend tests, production build, live data 5,530 equities, 6 indices, 100 sectors |

### Production smoke

Release `20260726-215448-d7d25de` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| API Ask Stock | Temporary authenticated account asked `为什么是青龙股份`; response returned HTTP 200, `kind=stock_analysis`, `symbol=SZ.002457`, and `name=青龙管业` |
| Browser Ask Stock | Real Chrome submitted `为什么是青龙股份`; the conversation rendered `青龙管业`, `SZ.002457`, local deterministic evidence, and did not render `一次只问一只股票` |
| Provider branding | The browser body did not contain `问财`, `WenCai`, or `iWenCai` |
| Responsive boundary | Real Chrome measured 1,280px desktop width and 390px mobile width with matching document scroll width |
| Service and data boundary | `/opt/aster-market/current` pointed to `/opt/aster-market/releases/20260726-215448-d7d25de`, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-qinglong-%@marketdesk.local` users were removed from the production database |

## 2026-07-27 Opportunity Lead Semantics

Opportunities now presents strategy output as `研究线索 / 待复核线索` instead of an implied participation signal. The page explicitly states that candidates are not participation advice and carries source context into Stock Lab, where a source note explains that the direct advice and evidence ledger are the final participation gate. A candidate that later says `暂不参与` is therefore no longer contradictory.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused frontend Opportunities test | Passed: 2 OpportunitiesPage tests, including the explicit lead/not-participation boundary, `复核是否参与` CTA, and source query link into Stock Lab |
| Focused backend opportunity tests | Passed: 6 opportunity analysis tests, including the new thesis participation boundary |
| Focused frontend Stock Lab test | Passed: 9 StockLabPage tests, including Opportunity source note and final-participation boundary |
| `make verify` | Passed: 112 backend tests, 38 frontend tests, production build, live data 5,532 equities, 6 indices, 100 sectors |

## 2026-07-27 Opportunity Pre-Judgement And Advice Reasons

Opportunity cards now show a deterministic lead pre-judgement badge such as `优先复核`, `待复核`, `可能暂不参与`, or `高风险线索` based on score, evidence coverage, market penalty, and risk flags. Stock Lab also moves the top three advice reasons directly under the direct suggestion so `暂不参与` or `等待回踩` explains itself before the deeper evidence sections.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused frontend Opportunities and Stock Lab tests | Passed: 11 tests, including the `可能暂不参与` lead badge and `为什么是这个建议` rationale block |
| Frontend typecheck | Passed after the lead badge and advice-rationale UI changes |
| `make verify` | Passed: 112 backend tests, 38 frontend tests, production build, live data 5,532 equities, 6 indices, 100 sectors |

### Production smoke

Release `20260727-115819-e9d9dbf` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health | Public `/healthz` returned `{"status":"ok"}` |
| Opportunity API semantics | Authenticated `trend` request returned `available=true`, 494 ranked leads, and response text included `线索策略`, `筛出线索`, and `是否参与以个股证据账本为准` |
| Frontend asset | Current JS asset contained `可能暂不参与`, `高风险线索`, `为什么是这个建议`, and `来自机会选股的研究线索` |
| Service and data boundary | `/opt/aster-market/current` pointed to `/opt/aster-market/releases/20260727-115819-e9d9dbf`, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-prejudge-%@marketdesk.local` user was removed from the production database |

## 2026-07-27 Stock Lab Opportunity Review Outcome

When a user opens Stock Lab from an Opportunity lead, the dossier now shows a `线索复核结果` block after the stock hero and before the direct advice. The block translates the final direct advice into a path-aware outcome: upgraded to trial, watch-only, or not upgraded to participation.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused frontend Stock Lab test | Passed: 9 StockLabPage tests, including the new `线索仅保留观察` review outcome for an Opportunity-sourced dossier |
| Frontend typecheck | Passed after adding the review outcome component |
| `make verify` | Passed: 112 backend tests, 38 frontend tests, production build, live data 5,532 equities, 6 indices, 100 sectors |

### Production smoke

Release `20260727-120614-677bb2e` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health | Public `/healthz` returned `{"status":"ok"}` |
| Stock API | Authenticated `SH.600519` dossier returned action `持有观察` with 4 rationale items |
| Frontend asset | Current JS asset contained `线索复核结果`, `线索仅保留观察`, `线索未升级为参与`, and `不因为曾入选线索而参与` |
| Service and data boundary | `/opt/aster-market/current` pointed to `/opt/aster-market/releases/20260727-120614-677bb2e`, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-review-outcome-%@marketdesk.local` user was removed from the production database |

## 2026-07-27 Opportunity Lead Layer Filtering

Opportunities now keeps the existing research-lead card layout but adds a compact lead-layer filter above the candidate list. Users can jump between `全部线索`, `优先复核`, `待复核`, `可能暂不参与`, and `高风险线索` without changing strategy presets, so the page better matches the earlier rule that opportunity output is a lead queue, not an automatic participation list.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused frontend Opportunities test | Passed: 2 OpportunitiesPage tests, including layer counts, `优先复核` filtering, `可能暂不参与` filtering, and source link preservation into Stock Lab |
| Frontend typecheck | Passed after adding memoized lead-layer counts and visible candidate filtering |
| `make verify` | Passed: 112 backend tests, 38 frontend tests, production build, live data 5,532 equities, 6 indices, 100 sectors |

### Production smoke

Release `20260727-122335-e0822be` was deployed to `stock.jiewat-kaka-fj.com`, linked from `/opt/aster-market/current`, and activated by `stock-ts.service`.

| Check | Production result |
| --- | --- |
| Health | Public `/healthz` returned `{"status":"ok"}` |
| Opportunity API | Authenticated `trend` request returned `available=true`, 494 ranked leads, and 50 candidate cards |
| Frontend asset | Current JS asset `/assets/index-4iBx8lBc.js` contained `线索分层筛选`, `全部线索`, `优先复核`, `高风险线索`, and the empty-layer copy |
| Service and data boundary | `/opt/aster-market/current` pointed to `/opt/aster-market/releases/20260727-122335-e0822be`, `stock-ts.service` was active, and `/opt/aster-market/current/data` was absent |
| Cleanup | Temporary `codex-lead-layer-%@marketdesk.local` users were removed from the production database |

## 2026-07-28 A-share Evidence And Market Intelligence

The pre-integration product is frozen by the annotated remote tag `v2`, whose peeled target remains `ec6f063d12580a23a33475763008b6b457ae8b13`. The release adds normalized A-share filings, research metadata, instrument themes, sector-flow leaders, Dragon-Tiger observations, and a CLS fast-news fallback without feeding any of those fields into deterministic scores.

Verification evidence:

| Gate | Result |
| --- | --- |
| Focused frontend | Passed: 18 tests across Stock Lab, Market, and Data Center |
| Backend lint and types | Ruff passed; mypy passed across 22 source files |
| Backend tests | Passed: 126 tests, including provider schema, partial aggregation, auth, TTL cache, and fallback coverage |
| Frontend tests | Passed: 41 tests across 8 files |
| Production build | Passed: Vite transformed 1,653 modules |
| Live market gate | Passed: 5,532 equities, 100.0% coverage, 6 indices, 100 sectors, fresh snapshot |
| Live evidence providers | `SH.600519` returned 5 CNINFO filings, 5 Eastmoney reports, and 8 themes; the latest Dragon-Tiger list and fast-news checks each returned 5 records |
| Capability health | CNINFO filings, Eastmoney research, themes, Dragon-Tiger, and Eastmoney fast news all reported `ready` during the live check |

Local browser acceptance:

| Check | Result |
| --- | --- |
| Local production service | Running at `http://127.0.0.1:8765`; `/healthz` returned `{"status":"ok"}` |
| Auth boundary | Registered temporary local account `codex-a-evidence-20260728-1526@marketdesk.local` and entered the authenticated workbench |
| Stock Lab | `SH.600519` rendered 20 CNINFO announcement links, 20 Eastmoney research links, instrument themes, and the no-score-change boundary copy |
| Theme clickthrough | Clicking the `食品饮料` theme opened `#/market?theme=BK0438...`, rendered `食品饮料题材简析`, and listed 30 related stocks including `SH.600519` |
| Theme flow summary | The theme dossier now derives its funding temperature from related-stock net-flow rows when the board endpoint supplies constituent flows |
| Market | Rendered A-share market intelligence, sector-flow leaders, latest Dragon-Tiger observations, and Stock Lab links |
| Flow leader clickthrough | Market sector-flow leaders are clickable and open the same sector dossier and stock-link list used by the board heatmap |
| Data Center | Rendered company filings, research, themes, Dragon-Tiger, Eastmoney fast news, and CLS fallback capability states |
| Responsive layout | Stock Lab, Market, and Data Center each measured `scrollWidth=390` at 390 x 844 and `scrollWidth=1280` at desktop width |
| Browser runtime | Playwright reported zero console errors and zero warnings after the authenticated desktop and mobile workflow |

Provider and product boundaries:

- The reviewed `a-stock-data` repository remains implementation research only and is not imported as a runtime dependency.
- Evidence endpoints cache only normalized in-memory values for bounded TTLs; raw payloads, document bodies, and PDFs are not persisted.
- `partial`, `empty`, and `unavailable` remain distinct, so a provider error cannot be interpreted as proof that no evidence exists.
- Public or commercial deployment still requires a fresh licensing review for CNINFO, Eastmoney, and CLS.

## 2026-07-29 Market Dossier Constituent Screener

Market sector and theme dossiers now behave as compact stock screeners after a user drills into a board, theme, or sector-flow leader.

Focused regression coverage:

```text
pnpm --dir frontend test --run src/features/market/MarketPage.test.tsx
```

Result: 9 Market page tests passed, including a new interaction that opens a sector from `板块资金确认`, verifies default net-flow ranking, switches to gain-first and amount-first sorting, and applies `只看净流入` / `只看上涨` range filters with the visible result count updated.

Browser acceptance to confirm before handoff:

- Authenticated `/market` opens sector-flow leaders into a dossier with `详情排序` and `详情范围` controls.
- Sorting changes the constituent order without changing the deterministic board summary or score evidence.
- Filters hide non-matching rows, show `显示 n / total`, and keep each stock linked to Stock Lab.
- 390px mobile width stacks the controls without document-level horizontal overflow.

Final local gate before public deployment:

| Gate | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 22 source files |
| Backend pytest | Passed, 128 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 44 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

Authenticated local browser acceptance passed on `http://127.0.0.1:8765/#/market` with a temporary Codex test account. A real Chrome session opened `食品饮料` from `板块资金确认`, rendered `详情排序` and `详情范围`, changed the detail ranking to gain-first, kept stock rows linked to Stock Lab, and reported no browser console/page errors. At 390 x 844 CSS pixels, document `scrollWidth` stayed 390 and the dossier controls stacked within a 320px panel.

## 2026-07-29 Morning Email Brief Preview

The morning email content layer now produces a deterministic text and HTML brief from existing authenticated market data. It does not add a new SMTP/provider dependency; the send channel can call the preview builder or `/api/v1/morning-email/preview` and keep provider access behind existing service boundaries.

Content contract:

- Subject and preheader summarize market regime, score, breadth, top sector flow, and top candidate.
- Body groups the morning workflow into opening conclusion, key evidence, sector flows, events/anomalies, candidate review, holdings/watchlist, and next actions.
- Candidate and personal sections include app deep links through the supplied `base_url`.
- The disclaimer states that the brief is research support only and does not change deterministic scores.

Focused checks:

```text
cd backend && uv run pytest -q tests/test_api.py -k morning_email_preview
cd backend && uv run ruff check src tests --fix && uv run mypy src
```

Result: the morning email preview test passed, backend imports were formatted, and mypy passed across 23 source files.

Full gate after adding the morning brief preview:

| Gate | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 44 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

Production morning-email sender compatibility check: the existing `stock-ts-morning-email.timer` calls `/opt/stock-ts/scripts/send_user_morning_reports.py`. That legacy sender was backed up as `scripts/send_morning_report.py.bak.20260729-email-v2`, then its content template was reorganized into opening conclusion, holdings priority, market/opportunity review, event/data risk, prediction feedback, and three current app links. A dry-run dispatch for `2026-07-30T08:45:00+08:00` returned `OK user=1: sent to 1 receiver(s)` without sending real email.

## 2026-07-29 Morning Brief Action Checklist Upgrade

The morning brief was upgraded from a readable digest to an opening-playbook format. The preview now includes a 09:25 / 09:45 / 10:30 checklist and an explicit forbidden-action section. Candidate lines state that confirmation requires market-relative strength, sector continuation, and price support; the email remains a review trigger rather than a trade signal.

Focused checks:

```text
cd backend && uv run pytest -q tests/test_api.py -k morning_email_preview
cd backend && uv run ruff check src tests --fix && uv run mypy src
```

Result: the preview test passed and mypy passed across 23 source files.

Production sender compatibility: the legacy `/opt/stock-ts/scripts/send_morning_report.py` sender was backed up as `send_morning_report.py.bak.20260729-email-v3`. It now converts unknown themes to `主题待确认`, appends an observation-only discipline note for unconfirmed themes, and adds an opening checklist section before the app links. The script compiles successfully with the production virtualenv.

Full gate after the action-checklist upgrade:

| Gate | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 44 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

## 2026-07-29 Morning Email Visual Layout Upgrade

The morning email was upgraded from a plain markdown-like layout into a card-based brief that puts the market state, recommended stock review list, sector-flow leaders, holdings risk, and opening checklist above the fold. The app preview keeps the deterministic morning-brief contract and uses email-client-friendly inline/table layout for the top metrics and sector cards.

Focused checks:

```text
cd backend && uv run pytest -q tests/test_api.py -k morning_email_preview
cd backend && uv run ruff check src tests --fix && uv run mypy src
```

Result: the preview route test passed, including HTML assertions for `今日大盘`, `大盘温度`, `推荐股票（需复核）`, `推荐股票 #1`, `板块资金主线`, and `开盘检查清单`; Ruff and mypy passed across 23 backend source files.

Production sender compatibility: the live legacy renderer at `/opt/stock-ts/src/stock_ts/notification.py` was backed up as `notification.py.bak.20260729-layout-v1`, then replaced with a visual renderer that parses the existing morning report sections into a hero, summary metric cards, recommended-stock cards, holdings-risk cards, and an opening-checklist timeline. The production script compiles successfully, generated HTML contains the new visual markers, and a dry-run dispatch for `2026-07-30T08:45:00+08:00` returned `OK user=1: sent to 1 receiver(s)` without sending real email.

## 2026-07-29 Morning Email Decision Console Upgrade

The visual morning email now behaves more like a pre-open decision console. The preview adds an opening-route strip, a market-breadth meter, candidate review priority labels, and a holdings-risk radar while keeping the original text fallback and app deep links intact.

Focused checks:

```text
cd backend && uv run pytest -q tests/test_api.py -k morning_email_preview
cd backend && uv run ruff check src tests --fix && uv run mypy src
```

Result: the preview route test passed with assertions for `今日开盘路线`, `市场广度仪表`, `上涨占比`, `复核级别`, and `持仓风险雷达`; Ruff and mypy passed across 23 backend source files.

Production sender compatibility: the legacy production renderer was backed up as `notification.py.bak.20260729-layout-v2`, then upgraded with the same opening-route, market-breadth, and review-priority markers. The production virtualenv compiled `src/stock_ts/notification.py` and `scripts/send_morning_report.py`, the generated HTML contained all new markers, and a dry-run account dispatch for `2026-07-30T08:45:00+08:00` returned `OK user=1: sent to 1 receiver(s)`.

## 2026-07-29 Core Workbench Decision Layer

The core workbench now adds a decision layer above the deep evidence sections. Stock Lab exposes a `个股复核作战台` immediately after the stock hero, combining the final action, confidence, evidence coverage, sector/theme handoff, invalidation condition, and next action. Market exposes a `市场作战台` above the breadth board, combining regime, breadth, funding mainline, event risk, and the next handoff into Opportunities.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx
pnpm --dir frontend test --run src/features/market/MarketPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Stock Lab passed 11 tests, Market passed 9 tests, and frontend typecheck passed. The new assertions verify `FINAL GATE`, `个股复核作战台`, theme/sector handoff into Market, `市场作战台`, breadth-derived route copy, funding-mainline drilldown, event-risk summary, and the Opportunities handoff.

## 2026-07-29 Sector Review Workbench

Market board and theme drilldowns now start with a `BOARD GATE` review desk before the constituent screener. The desk summarizes whether the board remains worth drilling into, how many constituents are rising, how many have net inflow, which stock leads price, which stock leads capital, and which evidence gaps still block conviction.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/market/MarketPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Market passed 9 tests and frontend typecheck passed. The new assertions verify `白酒板块复核工作台`, `酿酒概念题材复核工作台`, `BOARD GATE`, breadth/inflow spread metrics, lead-stock links into Stock Lab, missing-evidence copy, and that constituent sorting/filtering remains scoped to the screener rows rather than the review desk.

## 2026-07-29 Opportunity Queue Workbench

Opportunities now opens with a `QUEUE GATE` desk before diagnostics and the candidate table. The desk summarizes the active strategy, total candidates, reviewable vs observation-only counts, the top dossier to open first, and a deterministic handling route so the page behaves like a review queue rather than a raw stock list.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/opportunities/OpportunitiesPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Opportunities passed 2 focused tests and frontend typecheck passed. The new assertions verify `QUEUE GATE`, `线索队列`, the priority-first handling route, the top-candidate Stock Lab link, and queue shortcut filtering into the existing lead-layer table.

Full gate after the opportunity-queue upgrade:

| Gate | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 44 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

Public deployment smoke after the opportunity-queue upgrade:

| Check | Result |
| --- | --- |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-120858-86f7484` |
| Commit | `86f7484` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS asset contained `QUEUE GATE`, `线索队列`, `今日处理路线`, `第一张复核单`, and `队列筛选优先线索` |

## 2026-07-29 Stock Lab Evidence Audit Gate

Stock Lab now adds a `LEDGER GATE` evidence-audit desk immediately after the final decision deck. The desk condenses support evidence, contrary evidence, evidence gaps, and next review actions into a deterministic route such as `先补证据，不升级仓位`, so a lead opened from Opportunities can be checked before reading every detailed section.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Stock Lab passed 11 focused tests and frontend typecheck passed. The new assertions verify `证据总账`, `LEDGER GATE`, the evidence-coverage route, support/risk/gap counts, and that the audit desk appears before forecast and deep ledger sections.

Full gate and public deployment after the Stock Lab evidence-audit upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 44 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-121858-e905a0a` |
| Commit | `e905a0a` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS asset contained `LEDGER GATE`, `证据总账`, `先补证据，不升级仓位`, `反方证据占优，先守失效线`, and `证据够用，进入交易计划复核` |

## 2026-07-29 Market Board-To-Stock Handoff

Market sector and theme dossiers now add a `STOCK HANDOFF` block before the constituent screener. It highlights the first stocks to open from the board, explains whether the handoff is backed by price plus capital, price-only with a capital gap, capital-only, or merely active turnover, and carries board context into Stock Lab with a visible source note.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx src/features/market/MarketPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Market passed 9 focused tests, Stock Lab passed 12 focused tests, and frontend typecheck passed. The new assertions verify `STOCK HANDOFF`, priority stock links with board context, point-open reasons such as `价格与资金同向`, theme source gaps, and the Stock Lab `板块复核说明` note before the final evidence gates.

Full gate and public deployment after the Market board-to-stock handoff upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 45 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-122550-5faca6c` |
| Commit | `5faca6c` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS asset contained `STOCK HANDOFF`, `优先点开这几只`, `价格与资金同向`, `价格走强但资金缺口待补`, and `板块复核说明` |

## 2026-07-29 Ask Stock Source Context Bridge

Ask Stock now accepts source context from Stock Lab, Market board dossiers, and Opportunity leads. Stock Lab exposes a `带着证据去问股` handoff, Ask Stock shows the source bridge, preloads context-specific prompts, and prefixes the carried stock only for focused follow-ups so portfolio and broad screening questions remain separate.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Ask Stock passed 13 focused tests, Stock Lab passed 12 focused tests, and frontend typecheck passed. The new assertions verify `BOARD BRIDGE`, `QUEUE BRIDGE`, `问股来源上下文`, context prompt prefixing, a return link to Stock Lab, and the Stock Lab `带着证据去问股` handoff preserving opportunity and board parameters.

Full gate after the Ask Stock context bridge:

| Gate | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 47 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

Public deployment smoke after the Ask Stock context bridge:

| Check | Result |
| --- | --- |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-124201-82cc4a7` |
| Commit | `82cc4a7` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `问股来源上下文`, `BOARD BRIDGE`, `QUEUE BRIDGE`, `带着证据去问股`, `为什么它是板块前排样本`, and `线索能升级吗` |

## 2026-07-29 Ask Stock Decision Gates

Ask Stock stock-analysis answers now expose the same decision discipline as Stock Lab. The backend prepends explicit `FINAL GATE` and `LEDGER GATE` summaries to each deterministic stock answer, adds gate metrics alongside score, evidence coverage, confidence, price, and change, and the frontend renders a compact `ASK GATE` block before the answer body.

Focused checks:

```text
pytest -q backend/tests/test_ask_stock.py backend/tests/test_api.py -q
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
```

Result: backend Ask/API focused tests passed 54 tests, Ask Stock frontend passed 13 tests, and frontend typecheck passed. The new assertions verify `FINAL GATE`, `LEDGER GATE`, `ASK GATE`, and that the next review action is visible before the detailed evidence lists.

Full gate and public deployment after the Ask Stock decision-gate upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 47 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-125644-9c6b305` |
| Commit | `9c6b305` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `ASK GATE`, `FINAL GATE`, `LEDGER GATE`, `问股决策闸口`, and `先过门，再追问` |

## 2026-07-29 Ask Stock Gate-Aware Deep Links

Ask Stock gate cards now route the user back into the exact Stock Lab review section that matches the decision gate. Positive/ready gates open the trading-plan section, weak evidence opens the company-evidence section, and risk-dominant gates can open the invalidation/risk-control section. Stock Lab exposes stable section IDs and performs hash-based scrolling under the HashRouter shell.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Ask Stock passed 13 focused tests, Stock Lab passed 12 focused tests, and frontend typecheck passed. The assertions verify that `去看交易计划 →` targets `#stock-investment-advice`, `打开个股研究` targets `#stock-final-gate`, and Stock Lab exposes stable IDs for `stock-final-gate`, `stock-evidence-audit`, `stock-investment-advice`, and `stock-company-evidence`.

Full gate and public deployment after the Ask Stock deep-link upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 47 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-130800-cce0d23` |
| Commit | `cce0d23` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `去看交易计划`, `stock-investment-advice`, `stock-final-gate`, `stock-evidence-audit`, `stock-company-evidence`, and `stock-risk-controls` |

## 2026-07-29 Stock Lab Review Route Rail

Stock Lab now shows a `REVIEW ROUTE` rail after the stock hero and source-context note. It turns the long-form dossier into an explicit reading path: `FINAL GATE`, `LEDGER GATE`, trading plan, company evidence, and risk controls. Each route item links to the stable section anchors already used by Ask Stock deep links.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Stock Lab passed 12 focused tests and frontend typecheck passed. The assertions verify `个股复核路线`, `REVIEW ROUTE`, `按这条顺序读`, and that all five route links target `#stock-final-gate`, `#stock-evidence-audit`, `#stock-investment-advice`, `#stock-company-evidence`, and `#stock-risk-controls`.

Full gate and public deployment after the Stock Lab route-rail upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 47 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-131737-dcd3ee7` |
| Commit | `dcd3ee7` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `REVIEW ROUTE`, `按这条顺序读`, `个股复核路线`, `stock-review-rail`, and `个股复核区块导航` |

## 2026-07-29 Market Stock Handoff Review Routes

Market board and theme dossiers now turn each `STOCK HANDOFF` stock into a guided Stock Lab review route. Strong price-plus-flow leads open the trading-plan section, price-only leads open the evidence-audit ledger, flow-only leads open `FINAL GATE`, high-turnover but weak-direction leads open company evidence, and weak leads open risk controls. Constituent rows show the same first-stop hint so the compact screener and top handoff cards stay consistent.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/market/MarketPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Market passed 9 focused tests and frontend typecheck passed. The assertions verify board and theme handoff links include `#stock-investment-advice` or `#stock-evidence-audit`, and that route labels such as `先看交易计划` and `先看证据总账` render in the handoff cards and constituent rows.

Full gate and public deployment after the Market handoff route upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 47 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-132821-8516ebf` |
| Commit | `8516ebf` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `先看交易计划`, `先看证据总账`, `先看 FINAL GATE`, `先补公告研报`, `先看风控条件`, `stock-investment-advice`, `stock-evidence-audit`, `stock-risk-controls`, and `board-lead-route` |

## 2026-07-29 Ask Stock Post-Answer Review Route

Ask Stock answers now include a `REVIEW ROUTE` panel immediately after the decision gate. For single-stock answers it gives a four-step path: reopen `FINAL GATE`, inspect the evidence ledger, jump to the Stock Lab section selected by the gate, and continue with a concrete next question. The panel preserves the established Ask/Stock Lab anchors so the chat answer remains connected to deterministic evidence instead of becoming a dead-end conversation.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Ask Stock passed 13 focused tests and frontend typecheck passed. The assertions verify that `问后复核路线`, `Stock Lab 第一站`, and `下一句追问` render for stock answers, and that the route link targets `#stock-investment-advice` when `FINAL GATE` and `LEDGER GATE` permit a trading-plan review.

Full gate and public deployment after the Ask Stock review-route upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 47 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-134729-05dd4e9` |
| Commit | `05dd4e9` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `问后复核路线`, `REVIEW ROUTE`, `Stock Lab 第一站`, `下一句追问`, `如果风险触发，我应该怎么处理仓位`, `ask-review-route`, `stock-evidence-audit`, and `stock-investment-advice` |

## 2026-07-29 Stock Lab Compact Core View

Stock Lab now keeps the decision-making core visible by default and moves long-form evidence into an expandable `完整证据包`. The default page keeps `FINAL GATE`, `LEDGER GATE`, direct investment advice, and the future trend panel in the main reading path. The expandable package preserves historical validation, horizontal/vertical comparisons, analyst action map, structured conclusion, company evidence, analysis dimensions, next actions, price chart, raw score ledger, semantic research evidence, technical metrics, and risk controls. Deep links to `#stock-company-evidence`, `#stock-risk-controls`, and `#stock-score-ledger` automatically open the package.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Stock Lab passed 13 focused tests and frontend typecheck passed. The assertions verify that `完整证据包` is collapsed by default, opens manually, and opens automatically when a deep evidence anchor such as `#stock-company-evidence` is requested.

Full gate and public deployment after the Stock Lab compact-core upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 48 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-135725-c9e78ae` |
| Commit | `c9e78ae` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `完整证据包`, `展开技术图、公告研报、分析拆解和原始账本`, `核心结论已经在上方`, `stock-deep-dossier`, `FINAL GATE`, `LEDGER GATE`, `直接建议`, and `未来趋势` |

## 2026-07-29 Today Opening Desk

Today now starts with an `OPENING DESK` execution panel after the market risk rail. The panel turns the daily state into three first actions: market gate, priority review, and forbidden-action check. The gate adapts to regime, breadth, confidence, and risk budget: strong conditions allow opportunity review, cautious breadth keeps the user in market verification, and low risk budget sends the user to holdings risk first. The priority review deep-links the first candidate into Stock Lab `FINAL GATE` when available.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/app/App.test.tsx
pnpm --dir frontend typecheck
```

Result: App passed 6 focused tests and frontend typecheck passed. The authenticated Today route now asserts `今日开盘执行台`, `OPENING DESK`, `市场闸口`, `优先复核`, `今日禁区`, and the gate link into `#/opportunities`.

Full gate and public deployment after the Today opening-desk upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 48 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-140654-03f1749` |
| Commit | `03f1749` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `OPENING DESK`, `今日开盘执行台`, `市场闸口`, `优先复核`, `今日禁区`, `允许复核机会`, `只做前排复核`, `先守风险`, and `opening-desk` |

## 2026-07-29 Market Execution Console

Market now starts with a `MARKET PULSE / 大盘执行台` console before the broader evidence tables. The console turns the broad-market review into a compact execution read: gate verdict, breadth check, capital mainline, risk brake, and the next instruction. It preserves the existing `MARKET GATE`, sector-flow open action, event-risk summary, and opportunity funnel handoff, while adding adaptive states for `允许复核机会`, `只看前排板块`, and `先守风险`.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/market/MarketPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Market passed 9 focused tests and frontend typecheck passed. The assertions verify `MARKET PULSE · 大盘执行台`, `盘面三问`, breadth/mainline/risk checks, `执行指令`, `ORDER TAPE`, sector-flow action, event-risk summary, and the `/opportunities` handoff.

Full gate and public deployment after the Market execution-console upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 129 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 48 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |
| URL | `https://stock.jiewat-kaka-fj.com` |
| Release | `/opt/aster-market/releases/20260729-141838-6e977de` |
| Commit | `6e977de` |
| Health | Public `/healthz` returned `status=ok` |
| Services | `stock-ts.service` and `stock-ts-morning-email.timer` were active |
| Data boundary | `/opt/aster-market/current/data` was absent; runtime data remains external |
| Frontend asset | Current JS/CSS assets contained `MARKET PULSE`, `大盘执行台`, `允许复核机会`, `只看前排板块`, `先守风险`, `执行指令`, `盘面三问`, and `ORDER TAPE` |

## 2026-07-29 Opportunity Historical K-line Confirmation

Opportunity recommendations now keep the fast full-market snapshot screen, then batch-check up to the first 80 ranked leads with 120 trading days of K-line history before presenting the final lead queue. The history check adds a typed score and visible evidence for 20-day trend, 60-day trend, MA20 extension, 20-day volatility, 60-day drawdown, and 20-day volume ratio. Overextended, volatile, deep-drawdown, or rush-volume leads are downgraded with explicit risk flags before Stock Lab review.

Focused checks:

```text
pytest -q backend/tests/test_analysis.py -k 'opportunity'
pytest -q backend/tests/test_api.py -k 'opportunities'
pnpm --dir frontend test --run src/features/opportunities/OpportunitiesPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Opportunity analysis passed 7 focused tests, the opportunities API passed the historical-enrichment contract test, the Opportunity page passed 2 focused tests, and frontend typecheck passed. The new assertions verify the `历史确认` component/dimension, the `history_check` API payload, and the visible `HISTORY CHECK · 历史K线` card with trend, MA20, volatility, drawdown, and volume fields.

Full local gate after the Opportunity historical-confirmation upgrade:

| Check | Result |
| --- | --- |
| Backend lint | Passed, no findings |
| Backend mypy | Passed, 23 source files |
| Backend pytest | Passed, 133 tests, 1 third-party deprecation warning |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 49 tests across 8 files |
| Vite production build | Passed, 1,653 modules transformed |
| Live data | Passed: 5,533 equities, 100.0% coverage, 6 indices, 100 sectors, fresh observation |

## 2026-07-29 Opportunity Compact Expandable List

Opportunity candidates now render as a compact stock list by default. Each stock row shows only the rank, identity, final score, day change, score context, and lead badge; the thesis, historical K-line check, dimensions, invalidation rules, next actions, risk tags, and Stock Lab review link appear only after the user clicks that stock row. Strategy and lead-layer changes collapse open rows so the page stays scannable when 50 leads are returned.

Focused frontend checks:

```text
pnpm --dir frontend test --run src/features/opportunities/OpportunitiesPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Opportunity page passed 2 focused tests and frontend typecheck passed. The assertions verify collapsed rows start with `aria-expanded=false`, detail content and the review link are absent until a stock is clicked, and layer-filter changes keep the list compact before opening the selected stock.

## 2026-07-29 Ask Stock Conclusion-first Answers

Ask Stock now treats the chat answer as the product surface instead of replaying Stock Lab first. Stock-analysis responses start with a direct `结论：...` sentence from the deterministic answer builder, while FINAL GATE, LEDGER GATE, key metrics, review route, and scoring factors move behind an explicit `展开个股分析证据和复核路线` control. The visible default answer keeps only the conclusion, concise evidence, risks, next actions, and optional holding context.

Focused checks:

```text
pytest -q backend/tests/test_ask_stock.py backend/tests/test_api.py -k 'ask_stock'
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Ask Stock backend/API passed 25 focused tests, the Ask Stock page passed 13 focused tests, and frontend typecheck passed. The assertions verify stock answers no longer start with `FINAL GATE：`, default chat results hide the Stock Lab gate package, and clicking `展开个股分析证据和复核路线` reveals the detailed metrics and review route when needed.

## 2026-07-29 Ask Stock Short Conclusion and Target-price Follow-up

Ask Stock now treats target-price style follow-ups such as `未来可能涨到多少` as an action/price-target question. The deterministic answer no longer falls back to the full Stock Lab `dossier.conclusion`; it returns a short conclusion that says it cannot predict an exact target, shows the current price when available, and uses the take-profit/pressure discipline as the upper reference. Generic overview answers are also capped to a compact conclusion with score, evidence coverage, one support point, one risk point, and one next action.

Focused checks:

```text
pytest -q backend/tests/test_ask_stock.py backend/tests/test_api.py -k 'ask_stock'
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Ask Stock backend/API passed 27 focused tests, the Ask Stock page passed 13 focused tests, and frontend typecheck passed. The new assertions verify `未来可能涨到多少` is classified as an action question, returns a bounded direct answer under 180 characters, includes pressure/take-profit discipline, and does not include long Stock Lab sections like `技术面：` or `基本面：`.

## 2026-07-29 Market Page Structure Pass

The Market route now follows the research workflow instead of the raw component order: market gate, board/theme workbench, event verification, then full-market search. Sector/theme dossier panels are colocated with board heat so clicking a board no longer lands users above a separated full-market browser.

Focused regression:

```text
pnpm --dir frontend test --run src/features/market/MarketPage.test.tsx
```

Result: passed, 10 tests. Coverage asserts the new reading-order navigation, board/theme region placement before event radar, full-market browser placement after event verification, and existing sector/theme-to-stock handoff behavior.

## 2026-07-29 Ask Stock Movement Intent Fix

Ask Stock now treats recent price-move questions such as `最近大业股份怎么大跌` as a dedicated movement-explanation intent instead of falling through to generic risk or participation advice. The answer first quantifies recent 1/5/20-day movement, then explains only what local market evidence supports: moving-average break, drawdown, volume, fund flow, and board context. It explicitly avoids attributing the move to one unverified news item.

Red/green regression:

```text
uv run --directory backend pytest -q tests/test_ask_stock.py -k 'classifies_question_intent or builds_bounded_evidence_answer'
uv run --directory backend pytest -q tests/test_api.py -k 'recent_drop'
uv run --directory backend pytest -q tests/test_ask_stock.py tests/test_api.py -k 'ask_stock'
pnpm --dir frontend typecheck
```

Result: the first two tests initially failed because `最近大业股份怎么大跌` was not classified as movement and the response schema rejected that intent. After the fix, focused Ask Stock checks passed: 13 unit tests, 1 API regression, 30 combined Ask Stock API/unit tests, and frontend typecheck.

## 2026-07-29 Ask Stock Playbook And Fundamental/Catalyst Routes

Ask Stock now has a project-level answer playbook in `docs/ask-stock-answer-playbook.md`, adapted from common stock-analysis skill patterns without importing external runtime dependencies. The playbook fixes routing expectations for movement, risk, trend, valuation, fundamental, catalyst, action, portfolio, screening, and overview questions.

Implementation added two high-frequency stock-analysis routes:

- `fundamental`: handles basic quality, financial-report, revenue/profit/cash-flow/debt questions without pretending price action is fundamental evidence.
- `catalyst`: handles announcement, research-report, topic, event, and message/catalyst questions without inventing unverified news reasons.

Focused verification:

```text
uv run --directory backend pytest -q tests/test_ask_stock.py -k 'classifies_question_intent or builds_bounded_evidence_answer'
uv run --directory backend pytest -q tests/test_ask_stock.py tests/test_api.py -k 'ask_stock'
pnpm --dir frontend typecheck
```

Result: 17 intent/template unit tests passed, 35 combined Ask Stock API/unit tests passed, and frontend typecheck passed. The tests assert that basic-fundamental and catalyst questions no longer fall through to the generic overview/action answer.

## 2026-07-29 Ask Stock Scene Router UI

Ask Stock now exposes the answer playbook as a visible scene router in the left rail. Users can choose movement explanation, fundamental review, catalyst check, risk review, action discipline, or portfolio diagnosis before typing free-form text. When a stock context is active, scene prompts are generated for that stock; otherwise they use safe examples.

Focused verification:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Ask Stock page tests passed, 14 tests. The new regression clicks the `异动解释` scene route and verifies that it submits `最近大业股份怎么大跌`, renders the movement answer, and displays recent-move evidence.

## 2026-07-29 Global Research Router UI

The authenticated shell now has a topbar research router: `Cmd/Ctrl+K` focuses a global input, stock search uses the existing `/api/v1/search` route with the current auth token, search results jump straight to Stock Lab `FINAL GATE`, and unmatched free text can be handed to Ask Stock. Ask Stock also accepts `/ask?question=...` and auto-submits that inbound question so router handoffs produce an answer instead of a blank chat.

Focused verification:

```text
pnpm --dir frontend test --run src/app/App.test.tsx
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
```

Result: App shell tests passed, 7 tests; Ask Stock page tests passed, 15 tests; frontend typecheck passed. Coverage asserts keyboard focus, authenticated `/api/v1/search`, stock result rendering with sector context, Ask Stock handoff URL, and automatic Ask Stock submission from `question` search params.

## 2026-07-29 Recent Research Router

The global research router now remembers recently opened Stock Lab dossiers per authenticated account. Opening Stock Lab records the stock name, symbol, and sector in local storage; focusing the topbar router shows the latest research trail with direct `FINAL GATE` return buttons and one-click Ask Stock routes for risk and movement questions.

Focused verification:

```text
pnpm --dir frontend test --run src/app/App.test.tsx
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx
pnpm --dir frontend typecheck
```

Result: App shell tests passed, 8 tests; Stock Lab page tests passed, 14 tests; frontend typecheck passed. Coverage asserts account-scoped recent research loading, recent-stock shortcuts, Ask Stock risk/movement links, and Stock Lab writing the opened stock into the recent research trail.

## 2026-07-29 Stock Lab Ask Next Router

Stock Lab now adds an `ASK NEXT` strip immediately after the `FINAL GATE`. The strip turns the current dossier into four intent-aware Ask Stock routes: risk, movement, fundamental quality, and catalyst evidence. Each route carries the current stock symbol/name plus source context and a precise question, so users can continue from deterministic evidence into a conclusion-first chat without copying stock names or writing prompts manually.

Focused verification:

```text
pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Stock Lab page tests passed, 15 tests; frontend typecheck passed. Coverage asserts all four Ask Stock route URLs, preserved stock/source context, and placement between `FINAL GATE` and the evidence audit desk.

## 2026-07-29 Today Continue Research Desk

Today now surfaces the account-scoped recent research trail directly on the opening desk. When recent Stock Lab dossiers exist, the page shows a `CONTINUE` strip with direct links back to each stock's `FINAL GATE` plus one-click Ask Stock routes for risk, movement, and fundamental questions. This makes the morning workflow resume yesterday's research before scanning new noise.

Focused verification:

```text
pnpm --dir frontend test --run src/app/App.test.tsx
pnpm --dir frontend typecheck
```

Result: App shell tests passed, 9 tests; frontend typecheck passed. Coverage asserts the Today continue-research region, FINAL GATE deep link, and risk/movement/fundamental Ask Stock handoff URLs.

## 2026-07-29 Today Holding Risk Sentinel

Today now reads account-scoped `/api/v1/holdings` and places a `PORTFOLIO WATCH` sentinel directly below the opening desk when positions need attention. The sentinel ranks holdings by action severity, weight drift, losses, and risk flags; shows portfolio value, floating PnL, and the leading risk; then offers direct routes to holdings handling, Stock Lab `FINAL GATE`, and Ask Stock portfolio diagnosis. The query key includes the authenticated token scope so switching accounts cannot reuse another account's holding sentinel cache.

Focused verification:

```text
pnpm --dir frontend test --run src/app/App.test.tsx
pnpm --dir frontend typecheck
```

Result: App shell tests passed, 10 tests; frontend typecheck passed. Coverage asserts sentinel rendering, leading holding/risk flag/action copy, metrics, holdings route, Stock Lab deep link, Ask Stock holding-risk handoff URL, and account-scoped holdings cache behavior.

## 2026-07-29 Holdings Triage Desk

Holdings now behaves like a treatment desk after the Today sentinel. The page ranks holdings by action severity, rebalance value, drift, losses, and risk flags; surfaces the first item as a `NEXT POSITION` action deck; and adds direct handoffs to Stock Lab `FINAL GATE`, Ask Stock for the selected holding, and Ask Stock for portfolio ordering. The holdings page query key also includes the authenticated token scope to avoid stale account-scoped cache reuse.

Focused verification:

```text
pnpm --dir frontend test --run src/features/holdings/HoldingsPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Holdings page tests passed, 4 tests; frontend typecheck passed. Coverage asserts the action deck, rebalance metrics, Stock Lab deep link, holding-specific Ask Stock URL, portfolio-order Ask Stock URL, and risk-priority ordering before calmer holdings.

## 2026-07-29 Ask Stock Portfolio Bridge

Ask Stock now treats `from=holdings` and Today holding-risk handoffs as a dedicated portfolio bridge instead of a generic stock bridge. Holding handoff questions use the stable wording `我的持仓里{股票}风险怎么处理，要不要调仓`, the source card displays `PORTFOLIO BRIDGE`, links back to the holdings treatment desk, and provides holding/portfolio-specific follow-up prompts. Backend intent detection also recognizes natural holding treatment questions such as `我的持仓里贵州茅台风险怎么处理` as account-scoped portfolio diagnostics.

Focused verification:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx src/features/holdings/HoldingsPage.test.tsx src/app/App.test.tsx
pnpm --dir frontend typecheck
uv run --directory backend pytest -q tests/test_api.py -k 'ask_stock_named_portfolio_diagnostic or ask_stock_answers_portfolio_question_without_cross_account_leakage'
```

Result: Frontend focused tests passed, 30 tests; frontend typecheck passed; backend focused Ask Stock portfolio tests passed, 2 tests. Coverage asserts holdings/Today Ask Stock URLs, `PORTFOLIO BRIDGE` source context, holdings back-link, portfolio prompt carry behavior, and portfolio-analysis routing for named holding treatment questions.

## 2026-07-29 Opportunity Ask Bridge

Opportunities now closes the loop from a candidate lead to Ask Stock. The top candidate queue card exposes quick actions for `FINAL GATE`, lead-upgrade questioning, and risk questioning; expanded candidate rows also include stock review, lead-upgrade Ask Stock, and risk Ask Stock handoffs. All Ask links carry symbol, name, `from=opportunities`, preset, and a precise question so Ask Stock can render the existing opportunity bridge instead of a blank generic chat.

Focused verification:

```text
pnpm --dir frontend test --run src/features/opportunities/OpportunitiesPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Opportunities page tests passed, 2 tests; frontend typecheck passed. Coverage asserts top-candidate quick actions, encoded Ask Stock upgrade/risk URLs, expanded candidate action bars, and existing compact candidate expansion behavior.

## 2026-07-29 Watchlist Review Bridge

Watchlist now acts as a follow-up review desk instead of a passive note list. Each tracked stock links directly to Stock Lab `FINAL GATE`, exposes actions for `问是否继续跟` and `问失效条件`, and sends Ask Stock the stock symbol/name plus `from=watchlist` context. Ask Stock renders a dedicated `WATCH BRIDGE` source card with a back-link to the watchlist and follow-up prompts for continued tracking, invalidation, and next review points. The watchlist page query key also includes the authenticated token scope to avoid stale account-scoped cache reuse.

Focused verification:

```text
pnpm --dir frontend test --run src/features/watchlist/WatchlistPage.test.tsx src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
```

Result: Focused frontend tests passed, 18 tests; frontend typecheck passed. Coverage asserts watchlist `FINAL GATE` deep links, Ask Stock tracking/invalidation URLs, `WATCH BRIDGE` context, watchlist back-link, and source-stock carry behavior for follow-up prompts.

## 2026-07-29 Ask Stock Context Fallback

Ask Stock now sends explicit `context_symbol` / `context_name` with focused follow-up requests and the backend treats short contextual questions such as `为什么最近大跌` as stock-analysis follow-ups before attempting optional semantic screening. This prevents a stock page or board bridge conversation from falling into the `条件选股增强暂不可用` error when the user asks a natural short question without repeating the stock name.

Focused verification:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pytest backend/tests/test_api.py -k 'ask_stock'
pnpm --dir frontend typecheck
git diff --check
make verify
```

Result: Ask Stock frontend tests passed, 18 tests; backend Ask Stock tests passed, 14 tests; frontend typecheck passed; diff check passed; full `make verify` passed with backend 144 tests, frontend 61 tests, production build, and live-data quality gate.

## 2026-07-29 Ask Stock Structured Context

Ask Stock no longer rewrites user questions by prefixing the stock name. The frontend now keeps the user's wording intact and sends focused stock context separately through `context_symbol` / `context_name`; source handoffs also prefer the source stock over stale saved history for short questions. This avoids cross-stock contamination such as turning a fresh short question from a new stock page into an old-stock follow-up.

Focused verification:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
git diff --check
```

Result: Ask Stock frontend tests passed, 19 tests; frontend typecheck passed; diff check passed. Coverage asserts short manual follow-ups send structured context, source-context handoffs beat stale history, and user question text is not prefixed with the stock name.

## 2026-07-29 Ask Stock Visible Context Priority

Ask Stock now gives source handoff context priority in the visible UI as well as the request payload. When a user enters Ask Stock from a new stock/opportunity/board link while saved history still contains another stock, the side context, playbook examples, and composer placeholder now show the source stock instead of the stale historical stock.

Focused verification:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx
pnpm --dir frontend typecheck
git diff --check
```

Result: Ask Stock frontend tests passed, 19 tests; frontend typecheck passed; diff check passed. Coverage asserts stale-history handoffs from 贵州茅台 to 宁德时代 show 宁德时代 in the context panel and generated playbook prompts.

## 2026-08-16 Decision Intelligence Release Verification

The release combines the decision center, strategy-specific recommendation history, financial/news intelligence, OpenAI-compatible financial-model context, account-scoped monitoring, morning email delivery, ten-minute market/opportunity warming, holding workflow improvements, and the conclusion-first frontend redesign.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 31 source files |
| Backend tests | Passed, 223 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 84 tests across 11 files |
| Production build | Passed, 1,657 modules transformed |
| Live data | Passed, 5,542 equities, 100.0% coverage, 6 indices, 100 sectors |

Public acceptance at `https://stock.jiewat-kaka-fj.com/#/opportunities`:

- Deployment health returned `{"status":"ok"}` and `stock-ts.service` remained active.
- Desktop candidate expansion showed only decision, reason, risk, decision-change condition, and the ten-minute system-monitoring status by default.
- Low-confidence evidence was merged into one concise warning; strategy validation, historical metrics, thesis, and dimension evidence remained under `查看专业数据`.
- The removed `降级条件` and `后续核对` task blocks were absent before and after professional-data expansion.
- Desktop and 390-pixel layouts had no document overflow; the browser console reported no errors or warnings.
- The dedicated acceptance account created for the production browser test was removed after verification.

## 2026-08-22 Reminder Confidence And Interaction Verification

This release fixes the persistent-database rollback failure in Decision Change, adds filterable reminder categories and evidence confidence, prevents stale holding actions, clarifies recommendation maturity, removes Stock Lab's default Moutai assumption, and exposes Ask Stock through a backend financial-analysis Skill contract.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 31 source files |
| Backend tests | Passed, 226 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 86 tests across 11 files |
| Production build | Passed, 1,657 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

Persistent-data acceptance:

- Restarted the local service against the existing `data/marketdesk.db` without deleting or rewriting account data.
- Authenticated a temporary session for an account containing older decision rows with the retained `confidence` column.
- `GET /api/v1/decision-events` returned HTTP 200 with 17 events and a populated confidence sample; the temporary session was removed immediately afterward.
- Focused backend tests cover unknown future SQLite columns, confidence persistence, missing-history candidate gating, and hiding holding events after deletion.
- Frontend tests cover reminder filters, confidence semantics, recommendation maturity/distribution, deletion confirmation, explicit stock selection, and Ask Stock confidence.

Local production-build browser acceptance:

- Decision Change rendered 17 existing persisted events without HTTP 500, with candidate/holding and read-state filters plus per-event confidence.
- Combining `候选变化` and `未读` kept the filters visibly pressed and progressively rendered 10 of 16 matching events.
- Recommendation Review showed `0 / 6` mature samples, `未成熟 6`, and labelled `-4.85%` as a process return rather than a formal negative verdict.
- Stock Lab opened with no selected stock and the explicit `先选股票，再生成结论` state; entering `600519` loaded the dossier, while professional data remained unmounted until expansion.
- Desktop and 390-pixel checks had equal document/client widths, and the browser console reported no errors or warnings.

## 2026-08-22 Ask Stock To Stock Lab Context Verification

The navigation regression fixture starts with stale recent research for `SH.600519 贵州茅台`, returns a financial-Skill `llm_answer` for `SZ.300750 宁德时代`, then activates the main `个股` navigation item. The resulting route is `#/stocks?symbol=SZ.300750`; the stale Moutai symbol is absent.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 31 source files |
| Backend tests | Passed, 226 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 87 tests across 11 files |
| Production build | Passed, 1,657 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

## 2026-08-22 Quant Market Structure Verification

The release adopts the `jiewat-quant-panel/docs/reconstruction` workflow while keeping StockTS providers, deterministic analysis, confidence semantics, and Stock Lab as the final decision gate. Market, strategy registry, limit ladder, concept analysis, and industry analysis all consume authenticated `/api/v1/*` contracts.

Focused regressions prove:

- Dashboard metrics share one snapshot and expose breadth, distribution, liquidity, capital coverage, limit counts, sector extremes, and Stock Lab drill-downs.
- Stable strategy IDs show trigger, exit, hit count, confidence, and top candidate, then select the existing detailed candidate queue.
- Limit rules distinguish ST, main board, ChiNext/STAR, and Beijing; streaks use only unadjusted daily bars matching the target date.
- Delayed raw bars do not become current-day streak or one-word evidence, and historical ST status is not fabricated.
- Concept and industry use separate catalogs, preserve missing values as N/A, keep the last valid cross-section after refresh failure, and mark partial/stale results degraded.
- New structure pages cover search, sorting, mode switches, confidence language, unavailable/empty copy, and Stock Lab handoffs.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 32 source files |
| Backend tests | Passed, 235 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 91 tests across 12 files |
| Production build | Passed, 1,659 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

### Public release acceptance

Commit `7a76d5a` was pushed to `origin/codex/project-adjustments` and deployed as release `20260822-230633-7a76d5a` at `https://stock.jiewat-kaka-fj.com`.

Independent production checks confirmed:

- `/healthz` returned `status=ok`; `/opt/aster-market/current` resolves to the expected release; `stock-ts.service` and `stock-ts-morning-email.timer` are active; the persistent SQLite database remains under `/opt/aster-market/data`.
- The public index loads `index-QjsMrusz.js`, whose market chunk contains the new dashboard and structure routes. Refreshing an authenticated pre-release SPA tab loaded the new release without losing the session.
- At the desktop viewport, Market, Opportunities, Limit Ladder, Concept Analysis, and Industry Analysis rendered their expected workflow and had document width equal to client width.
- The Opportunities strategy library showed stable cards with hit count, entry conditions, exit conditions, confidence, and a linked candidate queue.
- The Limit Ladder switched from 80 limit-up stocks to 25 limit-down stocks and exposed 40% evidence confidence plus `封单数据 / 不可用 / 无盘口证据，不作估算`.
- Concept and industry pages exposed search, ranking controls, focus/membership evidence, and stock-analysis handoffs.
- At 390 x 844, all five pages measured `innerWidth=clientWidth=scrollWidth=390`; no document-level horizontal overflow occurred.
- The application emitted no origin-owned console error or warning. One observed error came from the user's Immersive Translate extension and was unrelated to StockTS.

## 2026-08-22 System Interaction Continuity Verification

Focused regressions cover three decision-continuity paths:

- A named financial-Skill answer for `SZ.300750 宁德时代` keeps its stock, intent, observation time, source, confidence, Stock Lab deep link, and stock-specific follow-up prompts.
- Decision Change renders `需要处理` before `提醒筛选`, while automatic monitoring remains the final information layer.
- A successful global refresh reads `meta.fetched_at` from the refresh response and confirms `全站数据已同步 · 更新于 <time>` without changing failure retention behavior.

Focused gate:

```text
pnpm --dir frontend test --run src/features/ask/AskStockPage.test.tsx src/features/decisions/DecisionCenterPage.test.tsx src/app/App.test.tsx
pnpm --dir frontend typecheck
```

Result: 39 focused tests passed across three files, and frontend typecheck passed.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 31 source files |
| Backend tests | Passed, 226 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 88 tests across 11 files |
| Production build | Passed, 1,657 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

## 2026-08-23 System Interface Redesign Verification

The frontend redesign adds a grouped decision/research/market-structure/verification shell, explicit workspace context, a persistent collapsible desktop rail, truthful reminder-service status, skeleton loading, local error isolation, terminal-style visual tokens, and a seven-entry mobile navigation.

Focused regression:

```text
pnpm --dir frontend typecheck
pnpm --dir frontend test --run src/app/App.test.tsx
```

Result: typecheck passed and all 14 application-shell tests passed. The new regression verifies navigation groups, route context, accessible collapse state, and `stockts:rail` persistence.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 32 source files |
| Backend tests | Passed, 235 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 92 tests across 12 files |
| Production build | Passed, 1,659 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

Local production-build health returned `{"status":"ok"}` on `127.0.0.1:8765`. Automated loopback navigation was blocked by the browser-control URL policy; the user completed local acceptance and approved deployment from the new branch.

### Public release acceptance

Commit `34704ce` was pushed to `origin/codex/project-adjustments` and deployed as release `20260823-000818-34704ce` at `https://stock.jiewat-kaka-fj.com` without modifying `main`.

- Public `/healthz`, the index, and the new JavaScript/CSS assets returned HTTP 200.
- The public index references `index-B6zz6A2N.js` and `index-BfpB0WJZ.css`; the bundles contain the new workspace brand, persistent rail key, reminder-service label, compact-rail rules, and skeleton state.
- `/opt/aster-market/current` resolves to the expected release, `stock-ts.service` and `stock-ts-morning-email.timer` are active, and the release contains no `data` directory.
- Persistent SQLite data remains external under `/opt/aster-market/data`.
- A post-fix gate rerun again passed lint, types, all 235 backend tests, all 92 frontend tests, and the production build. Its final live-source check encountered a transient Sina HTTP 456 after an earlier complete gate had passed with 5,548 equities and 100% coverage; no provider code changed in this release and the deployed service health remained normal.

## 2026-08-23 Interface Consistency Verification

The consistency pass introduces shared semantic tokens for UI/display/data typography, surfaces, panel/control radii, selected states, and numeric formatting. It applies those roles across the strategy registry, opportunity queue, stock conclusion, Ask Stock conversation/evidence, holdings execution surfaces, recommendation history, and market-structure workbenches. Responsive rules keep the opportunity decision desk and monitoring scope readable on desktop, tablet, and mobile.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 32 source files |
| Backend tests | Passed, 235 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 92 tests across 12 files |
| Production build | Passed, 1,659 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

Local production health returned `{"status":"ok"}` at `http://127.0.0.1:8765`. The user accepted the local workflow and requested public deployment from `main`.

### Public release acceptance

Commit `0cdff06` was pushed to `origin/main` and deployed as release `20260823-152204-0cdff06` at `https://stock.jiewat-kaka-fj.com`.

- Public `/healthz` returned `{"status":"ok"}` and the index referenced `index--_ubtXNb.js` plus `index-BlN5DOAz.css`.
- The public CSS contains `--font-display`, `--surface-selected`, and the new opportunity decision-desk grid rule, confirming the consistency bundle is active.
- `/opt/aster-market/current` resolves to the expected release; `stock-ts.service` and `stock-ts-morning-email.timer` are active.
- The release contains no runtime data directory, while persistent data remains present under `/opt/aster-market/data`.

## 2026-08-23 Long-page Containment Verification

The containment pass keeps the existing React/CSS system and applies one interaction rule across long routes: use available horizontal space first, show the highest-value subset initially, and let the user explicitly reveal or collapse the remainder.

Focused regressions verify:

- A 14-stock ladder level renders only the first 12 stocks, reveals the remaining two, and collapses back to 12.
- A 13-stock concept group renders only the first 12 constituents, reveals the remainder, and resets after changing groups.
- Seven recommendation days render as the latest six, load the seventh on request, and collapse back to six.
- Existing holdings behavior, stock handoffs, confidence copy, ladder direction changes, and market-group filtering remain intact.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 32 source files |
| Backend tests | Passed, 235 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 95 tests across 12 files |
| Production build | Passed, 1,659 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

Authenticated browser acceptance used the production bundle served at `http://127.0.0.1:8765`:

- At 1440 x 1000, Limit Ladder rendered 12 of 80 first-board stocks in three equal columns, had `scrollWidth=1440`, and reduced the document to 1,229px before expansion.
- At 390 x 844, the same page rendered a two-column stock grid and a 2 x 2 summary, had `scrollWidth=390`, and reduced document height from 2,861px to 2,037px.
- Concept Analysis kept its catalog inside a viewport-bounded scroll region and the selected-group workbench beside it on desktop.
- Recommendation Review initially rendered at most six days; Holdings kept the ten-day stock plan closed until requested.
- The checked routes emitted no browser console errors or warnings.

### Public release acceptance

Commit `ec90856` was pushed to `origin/main` and deployed as release `20260823-155528-ec90856` at `https://stock.jiewat-kaka-fj.com`.

- Public `/healthz` returned `{"status":"ok"}` and the index referenced `index-BA3EVQ3e.js` plus `index-DTop07XG.css`.
- `/opt/aster-market/current` resolves to the expected release; `stock-ts.service` and `stock-ts-morning-email.timer` are active.
- The release contains no runtime `data` directory, while `/opt/aster-market/data/marketdesk.db` remains present.
- At 1440 x 1000, the public ladder rendered 12 of 80 stocks in three columns with `scrollWidth=1440` and a reversible `再显示 68 只` control.
- At 390 x 844, the public ladder rendered two stock columns and a 2 x 2 summary with `scrollWidth=390`.
- The authenticated public session emitted no browser console errors or warnings.

## 2026-08-23 Core Task-flow Interaction Verification

Focused regressions cover the new interaction contracts:

- The opportunity decision desk precedes strategy selection, the compact switcher updates the active strategy summary, and candidate rows expose reversible judgement labels.
- Empty Holdings omits the portfolio overview and sort controls while rendering the registration form immediately.
- Empty Decision Change exposes three next-task links.
- Stock Lab exposes neutral candidate/ladder entry routes, and Ask Stock/Stock Lab suppress the duplicate global search input.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 32 source files |
| Backend tests | Passed, 235 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 95 tests across 12 files |
| Production build | Passed, 1,659 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

Authenticated local production-build acceptance at 1440 x 1000 and 390 x 844 verified:

- Opportunities reduced document height from approximately 2,025px to 1,692px on desktop; its decision desk begins at 178px and strategy switching updates the desk without changing scroll position.
- On mobile, the candidate list begins at approximately 852px instead of 1,247px, the strategy switcher remains horizontally operable, `查看判断` stays visible, and document `scrollWidth` equals 390px.
- Empty Holdings removes the zero-value overview and moves its form to the first screen; mobile inputs are 162px/336px wide with no document overflow.
- Stock Lab and Ask Stock each retain their local research input while the duplicate global search is absent.
- The only browser console error came from intentionally testing an expired token before registering the isolated local acceptance account; subsequent authenticated route requests were successful.

### Public release acceptance

Commit `c394042` was pushed to `origin/main` and deployed as release `20260823-161624-c394042` at `https://stock.jiewat-kaka-fj.com`.

- Public `/healthz` returned `{"status":"ok"}` and the index referenced `index-Ccp3p6Mr.js` plus `index-Dbr3osb9.css`.
- At 1440 x 1000, the candidate decision desk began at 178px, the compact strategy switcher followed at 468px, the list began at 805px, and document height was 1,692px with no overflow.
- Switching to `放量突破` updated both the live status and decision desk while preserving `scrollY=0`.
- At 390 x 844, the candidate list began at 852px, judgement labels remained visible, and document `scrollWidth` equalled 390px.
- Empty Holdings rendered onboarding and a directly usable form, omitted overview/sort controls, and used 162px/336px mobile input widths.
- Empty Decision Change exposed all three next-task links; Stock Lab kept its local search and omitted the global duplicate.
- The authenticated public session emitted zero console errors or warnings.
- `/opt/aster-market/current` resolves to the expected release; both systemd units are active, release data is absent, and the persistent database is present outside the release.

## 2026-08-23 Full-site Task-path Verification

Focused regressions cover the shared page frame, route heading semantics, task-path selection feedback, reduced-motion behavior, existing stock identity behavior, and all prior feature contracts.

Final repository gate:

```text
git diff --check
make verify
```

Result:

| Gate | Result |
| --- | --- |
| Backend lint | Passed |
| Backend types | Passed, 32 source files |
| Backend tests | Passed, 235 tests |
| Frontend types | Passed |
| Frontend tests | Passed, 97 tests across 13 files |
| Production build | Passed, 1,660 modules transformed |
| Live data | Passed, 5,548 equities, 100.0% coverage, 6 indices, 100 sectors |

Authenticated local production-build acceptance covered all ten routes at 1440 x 1000 and 390 x 844:

- Every route rendered one workbench heading and between two and four domain-specific task steps.
- Clicking the final task step on every route updated `aria-current` and moved focus to the intended section.
- All twenty desktop/mobile route checks reported zero document-level horizontal overflow.
- Stock Lab without a selected stock remained neutral and offered candidate/ladder starting points; its selected-stock path expands to identity, decision, questions, and evidence.
- Ask Stock exposed the active conversation object before the thread; Holdings kept the real-position boundary visible in its empty state.
- Concept and Industry kept the master-detail catalog readable and synchronized URL selection after filtering.
- Mobile navigation exposed all ten routes; entering Industry centered the active `行业` destination inside the 390px viewport.
