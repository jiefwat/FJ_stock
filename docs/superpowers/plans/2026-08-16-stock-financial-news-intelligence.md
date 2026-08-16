# Stock Financial And News Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured multi-period financial health and stock-specific news risk to every stock dossier, with conservative score effects and concise decision-first UI.

**Architecture:** Normalize Eastmoney financial and stock-news responses inside the existing provider boundary, then compute reproducible financial and news conclusions under `analysis/`. `MarketService.stock()` acquires both capabilities independently and returns their state in the existing `/api/v1/stocks/{symbol}` response; the React client renders only that API contract.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, httpx, pytest, React 19, TypeScript, TanStack Query, Vitest, Testing Library.

---

## File Map

- `backend/src/marketdesk/models.py`: normalized periods, stock-news items, health/sentiment conclusions, and dossier fields.
- `backend/src/marketdesk/providers/public_market.py`: Eastmoney financial/news requests and payload normalization.
- `backend/src/marketdesk/analysis/stock_intelligence.py`: deterministic financial scoring and hard-news risk classification.
- `backend/src/marketdesk/analysis/stock.py`: combine technical, financial, and news factors into the dossier.
- `backend/src/marketdesk/services.py`: concurrent capability acquisition and isolated degradation.
- `backend/tests/test_models.py`: strict contract and URL validation coverage.
- `backend/tests/test_public_provider.py`: financial JSON and news JSONP normalization coverage.
- `backend/tests/test_analysis.py`: bounded financial/news scoring coverage.
- `backend/tests/test_api.py`: stock API success and independent provider-failure coverage.
- `frontend/src/lib/api.ts`: shared financial/news response types.
- `frontend/src/features/stocks/StockLabPage.tsx`: concise financial-health and 30-day news cards plus expandable details.
- `frontend/src/features/stocks/StockLabPage.test.tsx`: visible conclusions, links, unavailable states, and expansion tests.
- `frontend/src/app/styles.css`: responsive card and detail-list layout.
- `docs/superpowers/market-intelligence-workbench/TODO.md`: completed release scope.

### Task 1: Strict Financial And News Contracts

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

Add tests constructing `FinancialPeriod`, `FinancialHealth`, `StockNewsItem`, and `StockNewsSentiment`. Assert timezone-aware timestamps, `http`/`https` news URLs, bounded impacts, and explicit `available=False` states.

```python
def test_stock_news_rejects_non_http_source_url() -> None:
    with pytest.raises(ValidationError):
        StockNewsItem(
            id="n1", title="风险提示", summary="", media="测试",
            url="javascript:alert(1)", published_at=datetime.now(UTC),
            sentiment="negative", hard_risk=True,
        )

def test_financial_and_news_impacts_are_bounded() -> None:
    with pytest.raises(ValidationError):
        FinancialHealth(available=True, score=80, score_impact=7, conclusion="稳健", periods=[])
    with pytest.raises(ValidationError):
        StockNewsSentiment(available=True, score_impact=-7, conclusion="有风险", items=[])
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `cd backend && uv run pytest -q tests/test_models.py`

Expected: collection fails because the four contracts do not exist.

- [ ] **Step 3: Add minimal strict models**

Define nullable structured fields for period data, `score_impact` bounds of `-10..6` and `-6..0`, sentiment literals, hard-risk counts, capability error fields, and a URL validator that accepts only `http` and `https`.

- [ ] **Step 4: Run the model tests and verify GREEN**

Run: `cd backend && uv run pytest -q tests/test_models.py`

Expected: all model tests pass.

### Task 2: Provider Normalization

**Files:**
- Modify: `backend/src/marketdesk/providers/public_market.py`
- Modify: `backend/tests/test_public_provider.py`

- [ ] **Step 1: Write failing provider tests**

Add fixture tests proving that `RPT_F10_FINANCE_MAINFINADATA` fields map to typed periods, duplicate report dates collapse to one period, numeric blanks remain `None`, and `stockts({...})` news JSONP maps to clean text, media, time, and source URL.

```python
periods = PublicMarketProvider.normalize_financial_periods(payload)
assert periods[0].revenue_yoy == 1.47
assert periods[0].net_profit_yoy == -1.95

items = PublicMarketProvider.normalize_stock_news(jsonp)
assert items[0].title == "贵州茅台半年报"
assert items[0].media == "证券时报"
```

- [ ] **Step 2: Run the provider tests and verify RED**

Run: `cd backend && uv run pytest -q tests/test_public_provider.py -k 'financial_periods or stock_news'`

Expected: failures report missing normalization and fetch methods.

- [ ] **Step 3: Implement bounded Eastmoney adapters**

Add `fetch_financial_periods(symbol, limit=5)` using the data-center endpoint and `fetch_stock_news(symbol, name, limit=20)` using the stock search endpoint. Keep request code in the provider, reject malformed JSON/JSONP with `ProviderUnavailable`, remove HTML tags from article text, deduplicate stable IDs, and sort newest first.

- [ ] **Step 4: Run provider tests and verify GREEN**

Run: `cd backend && uv run pytest -q tests/test_public_provider.py`

Expected: all public-provider tests pass.

### Task 3: Deterministic Financial And News Analysis

**Files:**
- Create: `backend/src/marketdesk/analysis/stock_intelligence.py`
- Modify: `backend/tests/test_analysis.py`

- [ ] **Step 1: Write failing analysis tests**

Cover profitable growth with sound cash conversion, profit decline with cash-flow divergence, high leverage, generic negative commentary, and a recent explicit investigation/profit-warning article.

```python
health = analyse_financial_health([healthy_period()])
assert 0 < health.score_impact <= 6

sentiment = analyse_stock_news([ordinary_comment(), investigation_news()])
assert sentiment.hard_risk_count == 1
assert -6 <= sentiment.score_impact < 0
```

Also assert positive news produces `score_impact == 0`, missing values are not treated as zero, and older hard-risk articles do not trigger a current penalty.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `cd backend && uv run pytest -q tests/test_analysis.py -k 'financial_health or stock_news'`

Expected: import failures because the analysis module does not exist.

- [ ] **Step 3: Implement conservative rules**

Score revenue/profit growth, ROE, cash conversion, and leverage only when present. Clamp the financial effect to `+6/-10`. Classify news with explicit positive/negative/hard-risk term sets, weight only recent hard risks, clamp news to `-6..0`, and return short Chinese conclusions and risk flags.

- [ ] **Step 4: Run analysis tests and verify GREEN**

Run: `cd backend && uv run pytest -q tests/test_analysis.py`

Expected: all deterministic-analysis tests pass.

### Task 4: Stock Service And API Integration

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/analysis/stock.py`
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Extend `FixtureProvider` with financial/news methods and assert `/api/v1/stocks/SH.600519` returns both blocks. Add one provider that fails finance and one that fails news; assert HTTP 200, the failed capability is unavailable, and the other remains available.

- [ ] **Step 2: Run the API tests and verify RED**

Run: `cd backend && uv run pytest -q tests/test_api.py -k 'stock_financial or stock_news'`

Expected: response fields are absent.

- [ ] **Step 3: Wire concurrent acquisition and score composition**

Add the two methods to `MarketProvider`. In `MarketService.stock()`, start K-line, semantic research, financial periods, and news together and convert each optional provider failure into its own unavailable analysis block. Pass available results into `analyse_stock()`, append visible `financial_health` and `news_risk` factors, and keep the total score reproducible from the displayed ledger.

- [ ] **Step 4: Run backend tests and verify GREEN**

Run: `cd backend && uv run pytest -q`

Expected: all backend tests pass.

### Task 5: Decision-first Stock Lab Cards

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/features/stocks/StockLabPage.tsx`
- Modify: `frontend/src/features/stocks/StockLabPage.test.tsx`
- Modify: `frontend/src/app/styles.css`

- [ ] **Step 1: Write failing UI tests**

Extend the dossier fixture and assert visible cards contain `财务健康`, latest period, profit trend, `新闻舆情`, hard-risk count, and a cited article link. Assert detailed periods/news stay inside the existing expandable package and unavailable states do not remove the stock conclusion.

- [ ] **Step 2: Run the component tests and verify RED**

Run: `cd frontend && pnpm test --run src/features/stocks/StockLabPage.test.tsx`

Expected: card headings and detail rows are absent.

- [ ] **Step 3: Render concise typed cards**

Add shared API types, render the two compact cards after the primary decision, use short conclusion phrases without operational narration, place full period/news rows in the deep dossier, and ensure all external links use `target="_blank" rel="noreferrer"`.

- [ ] **Step 4: Run frontend tests, types, and build**

Run: `cd frontend && pnpm test --run src/features/stocks/StockLabPage.test.tsx && pnpm typecheck && pnpm build`

Expected: component tests, TypeScript, and production build pass.

### Task 6: Verification And Public Deployment

**Files:**
- Modify: `docs/superpowers/market-intelligence-workbench/TODO.md`
- Modify only implementation files required by verification findings.

- [ ] **Step 1: Record the completed scope**

Add checklist entries for structured financial health, stock-specific sentiment, conservative score effects, independent degradation, and responsive Stock Lab presentation.

- [ ] **Step 2: Run repository gates**

Run: `git diff --check && make verify`

Expected: no whitespace errors; backend lint/types/tests and frontend lint/types/tests/build all exit zero.

- [ ] **Step 3: Complete real-browser acceptance**

Use the production build at desktop and 390px widths. Verify the two cards, expansion details, valid external links, independent unavailable copy, no horizontal overflow, and no long first-open spinner regression.

- [ ] **Step 4: Deploy and verify production**

Run:

```bash
DEPLOY_HOST=stock.jiewat-kaka-fj.com \
DEPLOY_USER=admin \
SSH_KEY=/Users/fangjie/.ssh/stockts_aliyun_deploy \
./deploy/deploy_public.sh
```

Then verify `https://stock.jiewat-kaka-fj.com/api/v1/health`, authenticate in the browser, open an A-share dossier, and confirm the deployed asset contains the new card labels.
