# Ask Stock Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an authenticated Ask Stock page that answers named-stock questions from the deterministic dossier and optionally sends broad natural-language screens through the existing semantic provider.

**Architecture:** A pure `analysis/ask_stock.py` module resolves stocks, classifies question intent, and composes evidence-backed answers from `StockDossier`. `MarketService` owns orchestration and optional semantic fallback; `IwencaiProvider` owns external payload normalization. React adds one route and page while continuing to use only `/api/v1/*`.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, httpx, pytest, React 19, TypeScript, TanStack Query, Vitest, Testing Library, CSS.

---

### Task 1: Deterministic named-stock answer engine

**Files:**
- Create: `backend/src/marketdesk/analysis/ask_stock.py`
- Create: `backend/tests/test_ask_stock.py`
- Modify: `backend/src/marketdesk/models.py`

- [ ] **Step 1: Write failing resolution and intent tests**

Create fixtures for `SH.600519 贵州茅台` and `SZ.000858 五粮液`. Assert that `resolve_stock_question()` resolves either a six-digit code or contained Chinese name, raises `StockQuestionNotFound` when neither exists, and raises `AmbiguousStockQuestion` when both names occur. Assert that `classify_stock_question()` returns `risk`, `trend`, `valuation`, `action`, or `overview` for representative Chinese questions.

```python
def test_resolves_one_stock_by_code_or_name() -> None:
    assert resolve_stock_question("600519 的趋势怎么样", quotes()).symbol == "SH.600519"
    assert resolve_stock_question("贵州茅台主要风险", quotes()).symbol == "SH.600519"


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("贵州茅台有哪些风险", "risk"),
        ("贵州茅台技术趋势怎么样", "trend"),
        ("贵州茅台估值贵不贵", "valuation"),
        ("贵州茅台仓位和止损怎么定", "action"),
        ("贵州茅台怎么样", "overview"),
    ],
)
def test_classifies_question_intent(question: str, intent: str) -> None:
    assert classify_stock_question(question) == intent
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd backend && uv run pytest -q tests/test_ask_stock.py`

Expected: collection fails because `marketdesk.analysis.ask_stock` does not exist.

- [ ] **Step 3: Add strict response models and minimal resolution**

In `models.py`, add `AskStockResponse` with `kind`, `question`, `intent`, optional `symbol` and `name`, `answer`, evidence/risk/action lists, optional `observed_at`, `source`, `disclaimer`, `columns`, and scalar-only `rows`. Add `SemanticScreenResult` with bounded columns and rows.

In `analysis/ask_stock.py`, normalize whitespace, match six-digit codes before stock names, deduplicate matches by symbol, and implement keyword classification. Do not perform provider calls or market refreshes in this module.

- [ ] **Step 4: Add failing answer-composition tests**

Build a `StockDossier` fixture and assert:

- risk answers use `bear_case` and `invalidation`;
- trend answers use `trend_forecast.summary` and drivers;
- valuation answers use available `valuation` dimensions/comparisons;
- action answers use `investment_advice` and stop discipline;
- overview answers retain the existing conclusion and evidence coverage;
- every response contains the market observation time and research-only disclaimer.

- [ ] **Step 5: Implement `build_stock_answer()` and verify GREEN**

Compose concise plain-text responses from existing dossier fields. Keep evidence lists to five items, risks to four, and next actions to four. Never recalculate the stance score.

Run: `cd backend && uv run pytest -q tests/test_ask_stock.py`

Expected: all Ask Stock analysis tests pass.

- [ ] **Step 6: Commit the deterministic engine**

```bash
git add backend/src/marketdesk/analysis/ask_stock.py backend/src/marketdesk/models.py backend/tests/test_ask_stock.py
git commit -m '[问股分析] 增加确定性问题解析与回答'
```

### Task 2: Optional semantic screening provider

**Files:**
- Modify: `backend/src/marketdesk/providers/iwencai.py`
- Modify: `backend/src/marketdesk/providers/public_market.py`
- Modify: `backend/tests/test_iwencai_provider.py`

- [ ] **Step 1: Write failing provider-normalization tests**

Add tests covering payloads with `data` as a list of mappings. Verify that code/name columns sort first, nested values are discarded, strings are whitespace-normalized and bounded, duplicate/missing columns are handled, and results stop at 20 rows and 12 columns.

```python
def test_normalize_stock_screen_bounds_dynamic_payload() -> None:
    payload = {"data": [{"股票简称": " 贵州茅台 ", "股票代码": "600519", "市盈率": 23.1}]}
    result = normalize_stock_screen(payload)
    assert result.columns[:2] == ["股票代码", "股票简称"]
    assert result.rows == [{"股票代码": "600519", "股票简称": "贵州茅台", "市盈率": 23.1}]
```

- [ ] **Step 2: Run the provider test and verify RED**

Run: `cd backend && uv run pytest -q tests/test_iwencai_provider.py`

Expected: fail because `normalize_stock_screen` is missing.

- [ ] **Step 3: Implement bounded normalization and query method**

Add `normalize_stock_screen(payload, row_limit=20, column_limit=12)` and `IwencaiProvider.query_stocks(question, limit=20)`. Post `query`, `query_type=stock`, and `limit` to the configured endpoint with the existing bearer credential. Raise `ProviderUnavailable` for absent configuration, HTTP errors, invalid JSON, or empty usable rows. Never include credential values in exceptions.

- [ ] **Step 4: Delegate through `PublicMarketProvider`**

Add `query_stock_screen(question, limit=20)` that delegates to `research_provider`, updates semantic-provider health to `ready`, `empty`, or `partial`, and propagates `ProviderUnavailable` so the API can render an honest unavailable state.

- [ ] **Step 5: Verify provider tests and commit**

Run: `cd backend && uv run pytest -q tests/test_iwencai_provider.py`

Expected: all provider tests pass.

```bash
git add backend/src/marketdesk/providers/iwencai.py backend/src/marketdesk/providers/public_market.py backend/tests/test_iwencai_provider.py
git commit -m '[问财接入] 增加受限自然语言选股查询'
```

### Task 3: Authenticated Ask Stock API

**Files:**
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add tests that prove:

1. Anonymous `POST /api/v1/ask-stock` returns 401.
2. An authenticated name/code question returns `stock_analysis` and the matched symbol.
3. A question shorter than 2 or longer than 160 characters returns 422.
4. Multiple local stocks return 422 with `一次只问一只股票`.
5. A broad query uses a provider fixture's `query_stock_screen()` and returns `semantic_screen`.
6. A broad query without semantic support returns 503 without affecting later `/api/v1/today` requests.

- [ ] **Step 2: Run API tests and verify RED**

Run: `cd backend && uv run pytest -q tests/test_api.py -k ask_stock`

Expected: requests return 404 because the endpoint is absent.

- [ ] **Step 3: Add service orchestration**

Implement `MarketService.ask_stock(question)`:

1. load the current market snapshot;
2. try local stock resolution;
3. for one match, call the existing `stock(symbol)` and `build_stock_answer()`;
4. for no match, call an optional `query_stock_screen` provider method;
5. return a bounded `semantic_screen` response or raise `ProviderUnavailable`.

Keep `MarketProvider` structural typing compatible with existing fixture providers by discovering semantic screening with `getattr`, as the service already does for optional enrichment.

- [ ] **Step 4: Add request validation and error mapping**

Add an API-local `AskStockRequest(StrictModel)` with `question: str = Field(min_length=2, max_length=160)` and a validator that trims and rejects whitespace-only input. Add `POST /api/v1/ask-stock`, returning `AskStockResponse`. Map ambiguous questions to 422, missing semantic configuration/provider failure to 503, and keep authentication in the existing application middleware.

- [ ] **Step 5: Verify backend boundary and commit**

Run:

```bash
cd backend
uv run pytest -q tests/test_ask_stock.py tests/test_iwencai_provider.py tests/test_api.py -k 'ask_stock or stock_screen or stock_question'
uv run ruff check src tests
uv run mypy src
```

Expected: focused tests pass, Ruff has no findings, and mypy reports no issues.

```bash
git add backend/src/marketdesk/services.py backend/src/marketdesk/api.py backend/tests/test_api.py
git commit -m '[问股接口] 接入本地分析与问财降级'
```

### Task 4: Ask Stock page

**Files:**
- Create: `frontend/src/features/ask/AskStockPage.tsx`
- Create: `frontend/src/features/ask/AskStockPage.test.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/styles.css`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] **Step 1: Write failing page tests**

Render `AskStockPage` with mocked fetch responses and assert:

- the question label, examples, and submit button render;
- clicking a suggested risk question populates and submits the input;
- pending state disables the button;
- a named-stock answer shows matched name/symbol, source, observation time, evidence, risks, actions, and disclaimer;
- a semantic response renders only the returned bounded columns and rows;
- HTTP 422 and 503 display the backend detail without removing the typed question.

- [ ] **Step 2: Run page tests and verify RED**

Run: `cd frontend && pnpm test --run src/features/ask/AskStockPage.test.tsx`

Expected: fail because the Ask Stock page does not exist.

- [ ] **Step 3: Add API types and page implementation**

Add `AskStockResponse` and scalar-row types to `frontend/src/lib/api.ts`. Build the page with local question state and a TanStack mutation calling `POST /api/v1/ask-stock`. Render all returned text as React text nodes, never `dangerouslySetInnerHTML`. Use a horizontally contained table wrapper for semantic results.

- [ ] **Step 4: Add navigation and route**

Import a suitable existing Lucide icon, add `问股` to the `nav` array, and add `<Route path="/ask" element={<AskStockPage />} />`. Extend `App.test.tsx` to prove the new route remains behind the application login gate and is reachable after a valid session.

- [ ] **Step 5: Add scoped responsive styles**

Append `.ask-*` styles only. Use the existing CSS variables, panel borders, Songti headings, DIN metadata, and 900 px breakpoint. At mobile width, stack the composer and evidence sections, constrain the result table to local horizontal scrolling, and keep `body` free from horizontal overflow.

- [ ] **Step 6: Verify frontend and commit**

Run:

```bash
cd frontend
pnpm test --run src/features/ask/AskStockPage.test.tsx src/app/App.test.tsx
pnpm typecheck
pnpm build
```

Expected: focused tests pass, TypeScript exits 0, and Vite produces the production bundle.

```bash
git add frontend/src/features/ask frontend/src/lib/api.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx frontend/src/app/styles.css
git commit -m '[问股界面] 增加交互式证据问答页面'
```

### Task 5: Acceptance, documentation, and deployment

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/market-intelligence-workbench/TODO.md`
- Modify: `docs/superpowers/market-intelligence-workbench/test.md`

- [ ] **Step 1: Document boundaries and configuration**

Document the named-stock local path, optional `MARKETDESK_IWENCAI_ENDPOINT` and `MARKETDESK_IWENCAI_API_KEY`, the fact that credentials stay server-side, the 20-row/12-column limit, and the explicit unavailable behavior. Do not document or commit credential values.

- [ ] **Step 2: Run the complete repository gate**

Run: `git diff --check && make verify`

Expected: no whitespace errors; backend lint/types/tests, frontend types/tests/build, and live-data quality all pass.

- [ ] **Step 3: Complete production-build browser acceptance**

Verify at desktop and 390 px:

1. Anonymous users still see only the login page.
2. An authenticated user can open `问股`.
3. `贵州茅台现在主要风险是什么` returns a named-stock answer with evidence and observation time.
4. A broad screen returns a bounded table when semantic research is configured, or an explicit configuration message when it is not.
5. No question or result causes document-level horizontal overflow.

- [ ] **Step 4: Deploy without touching persistent data**

Use `deploy/deploy_public.sh`. Confirm the release archive excludes `data`, the systemd unit still points to `/opt/aster-market/data`, and `release-2026-07-25` remains unchanged. Do not add a Wencai credential to Git or the release archive.

- [ ] **Step 5: Run live smoke checks and record evidence**

Verify `/healthz`, anonymous Ask Stock 401, authenticated named-stock response, page navigation, and service status. Update the active test evidence with the deployed release ID and observed behavior, then commit the documentation and release record.
