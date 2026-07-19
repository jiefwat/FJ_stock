# Analyst Workflow V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current market dashboard into a trustworthy daily analyst loop with real strategy differences, reproducible stock evidence, editable research notes, and explicit data feedback.

**Architecture:** Extend normalized response contracts and deterministic analysis under `backend/src/marketdesk/analysis/`, then render the new evidence-ledger data through the existing React routes. Provider access remains unchanged and browser code continues to call only `/api/v1/*`.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, React 19, TypeScript, TanStack Query, Vitest, Testing Library, SVG, CSS.

---

## File Map

- `backend/src/marketdesk/models.py`: strategy metadata and stock evidence contracts.
- `backend/src/marketdesk/analysis/opportunities.py`: preset availability, gates, score coverage, and market penalties.
- `backend/src/marketdesk/analysis/stock.py`: reproducible multi-factor stance.
- `backend/tests/test_analysis.py`: deterministic analysis regression coverage.
- `backend/tests/test_api.py`: response-contract and watchlist update coverage.
- `frontend/src/lib/api.ts`: typed V2 API contracts and neutral percentage formatting.
- `frontend/src/features/opportunities/OpportunitiesPage.tsx`: strategy rules, unavailable states, and visible risk evidence.
- `frontend/src/features/stocks/StockTrend.tsx`: close plus MA overlays.
- `frontend/src/features/stocks/StockLabPage.tsx`: evidence ledger and editable watchlist composer.
- `frontend/src/features/stocks/StockLabPage.test.tsx`: stock workflow regression coverage.
- `frontend/src/features/watchlist/WatchlistPage.tsx`: editable research journal.
- `frontend/src/features/watchlist/WatchlistPage.test.tsx`: edit/save workflow.
- `frontend/src/features/today/TodayPage.tsx`: actionable briefing and confidence formatting.
- `frontend/src/features/market/MarketPage.tsx`: factor explanations and progressive sector disclosure.
- `frontend/src/features/data/DataCenterPage.tsx`: freshness, timestamps, and refresh result.
- `frontend/src/app/styles.css`: evidence-ledger and journal desktop styles.

### Task 1: Honest Opportunity Strategies

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/analysis/opportunities.py`
- Test: `backend/tests/test_analysis.py`

- [ ] **Step 1: Write failing strategy tests**

Add tests that assert `trend` excludes a 10% chase candidate, `oversold_rebound` selects a negative-return value candidate, `capital_confirmed` is unavailable without flow coverage, and risk-off applies a visible score penalty.

```python
def test_opportunity_presets_are_distinct_and_explain_unavailable_data() -> None:
    rows = [
        equity(symbol="SH.600010", change_pct=10.0),
        equity(symbol="SH.600011", change_pct=3.0),
        equity(symbol="SH.600012", change_pct=-3.0),
    ]
    trend = rank_candidates(rows, "balanced", "trend")
    oversold = rank_candidates(rows, "balanced", "oversold_rebound")
    capital = rank_candidates([equity(net_flow=None)], "balanced", "capital_confirmed")
    assert [item.quote.symbol for item in trend.candidates] == ["SH.600011"]
    assert [item.quote.symbol for item in oversold.candidates] == ["SH.600012"]
    assert capital.available is False
    assert "资金流" in capital.unavailable_reason

def test_risk_off_penalty_is_visible() -> None:
    candidate = rank_candidates([equity(change_pct=3.0)], "risk_off", "trend").candidates[0]
    assert candidate.context_penalty == 15
    assert candidate.score == candidate.base_score - candidate.context_penalty
```

- [ ] **Step 2: Run the focused tests and confirm expected failures**

Run: `cd backend && uv run pytest -q tests/test_analysis.py -k 'presets_are_distinct or risk_off_penalty'`

Expected: fail because opportunity availability and score-context fields do not exist and presets are not applied.

- [ ] **Step 3: Add contracts and minimal deterministic rules**

Add `base_score`, `context_penalty`, and `evidence_coverage` to `RankedCandidate`; add `available`, `unavailable_reason`, and `rules` to `OpportunityResult`. Implement preset-specific eligibility before score calculation and apply a 15-point risk-off or 8-point cautious penalty.

- [ ] **Step 4: Run analysis tests**

Run: `cd backend && uv run pytest -q tests/test_analysis.py`

Expected: all analysis tests pass.

### Task 2: Reproducible Stock Evidence

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/analysis/stock.py`
- Test: `backend/tests/test_analysis.py`

- [ ] **Step 1: Write failing evidence-ledger tests**

```python
def test_stock_stance_uses_multiple_visible_factors() -> None:
    result = analyse_stock(equity(pe=24, change_pct=2), trending_bars())
    assert result.evidence_coverage < 1
    assert {item.key for item in result.score_factors} >= {"price_ma20", "ma_stack", "rsi", "volatility", "valuation"}
    assert round(50 + sum(item.impact for item in result.score_factors), 2) == result.stance_score

def test_high_volatility_creates_bear_evidence() -> None:
    result = analyse_stock(equity(), volatile_bars())
    assert any("波动" in item for item in result.bear_case)
```

- [ ] **Step 2: Run the focused tests and confirm expected failures**

Run: `cd backend && uv run pytest -q tests/test_analysis.py -k 'multiple_visible_factors or high_volatility'`

Expected: fail because `score_factors` and `evidence_coverage` do not exist.

- [ ] **Step 3: Implement the deterministic factor ledger**

Add a `StockScoreFactor` model with `key`, `label`, `impact`, `signal`, `evidence`, and `available`. Compute the stance from the factor impacts listed in the V2 design and generate bull/bear cases from positive/negative impacts. Include missing sector, capital, and announcement evidence in coverage.

- [ ] **Step 4: Run backend tests**

Run: `cd backend && uv run pytest -q`

Expected: all backend tests pass.

### Task 3: Decision-first Today, Market, Opportunities, And Stock Lab

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/features/today/TodayPage.tsx`
- Modify: `frontend/src/features/market/MarketPage.tsx`
- Modify: `frontend/src/features/opportunities/OpportunitiesPage.tsx`
- Modify: `frontend/src/features/stocks/StockTrend.tsx`
- Modify: `frontend/src/features/stocks/StockLabPage.tsx`
- Modify: `frontend/src/features/stocks/StockLabPage.test.tsx`
- Modify: `frontend/src/app/styles.css`

- [ ] **Step 1: Write failing Stock Lab interaction tests**

Extend the fixture with `score_factors` and `evidence_coverage`, then assert that MA5/20/60 legends render, an existing watchlist item is detected, and an unwatched stock opens an editable thesis form before POST.

```tsx
expect(await screen.findByText("MA5")).toBeInTheDocument();
expect(screen.getByText("证据覆盖 55%")).toBeInTheDocument();
fireEvent.click(screen.getByRole("button", { name: "加入观察" }));
expect(screen.getByLabelText("研究逻辑")).toBeInTheDocument();
```

- [ ] **Step 2: Run the frontend test and confirm expected failures**

Run: `cd frontend && pnpm test --run src/features/stocks/StockLabPage.test.tsx`

Expected: fail because the evidence ledger, MA legends, and composer do not exist.

- [ ] **Step 3: Implement typed evidence-ledger UI**

Render explicit unavailable strategy panels, readable strategy rules, candidate risk flags, base score and context penalty. Render stock close and moving averages as four SVG polylines, show the stock factor ledger and evidence coverage, and add an editable watchlist composer. Today links each next action and formats confidence without a plus sign. Market initially shows twelve sectors with a show-all control and factor evidence text.

- [ ] **Step 4: Run frontend tests, types, and build**

Run: `cd frontend && pnpm test --run && pnpm typecheck && pnpm build`

Expected: all frontend checks pass.

### Task 4: Editable Watchlist And Auditable Refresh

**Files:**
- Create: `frontend/src/features/watchlist/WatchlistPage.test.tsx`
- Modify: `frontend/src/features/watchlist/WatchlistPage.tsx`
- Modify: `frontend/src/features/data/DataCenterPage.tsx`
- Modify: `frontend/src/app/styles.css`

- [ ] **Step 1: Write failing watchlist editor test**

```tsx
expect(await screen.findByRole("link", { name: "贵州茅台" })).toHaveAttribute("href", "/stocks?symbol=SH.600519");
fireEvent.change(screen.getByLabelText("研究逻辑"), { target: { value: "等待估值回落" } });
fireEvent.click(screen.getByRole("button", { name: "保存研究记录" }));
expect(await screen.findByText("已保存")).toBeInTheDocument();
```

- [ ] **Step 2: Run the test and confirm expected failure**

Run: `cd frontend && pnpm test --run src/features/watchlist/WatchlistPage.test.tsx`

Expected: fail because the stock link, editors, save action, and feedback do not exist.

- [ ] **Step 3: Implement journal editing and refresh feedback**

Split each watchlist row into a focused card with local draft state, explicit save, retryable error text, Stock Lab link, and last-updated time. Expand Data Center to display observation time, fetch time, freshness, coverage and provider errors; use the refresh mutation result for a visible completion message.

- [ ] **Step 4: Run all frontend checks**

Run: `cd frontend && pnpm test --run && pnpm typecheck && pnpm build`

Expected: all frontend checks pass.

### Task 5: Full Verification And Browser Acceptance

**Files:**
- Modify: `docs/superpowers/market-intelligence-workbench/TODO.md`
- Modify: `docs/superpowers/market-intelligence-workbench/test.md`
- Modify only implementation files required by findings.

- [ ] **Step 1: Run the repository gate**

Run: `make verify`

Expected: backend lint/types/tests, frontend types/tests/build, and live-data quality all pass.

- [ ] **Step 2: Start the production build and complete the analyst workflow**

Verify in a real browser:

1. Today explains regime evidence and links into Opportunities.
2. Trend and oversold strategies produce different candidates.
3. Capital and sector strategies show explicit unavailable states with the current data.
4. A candidate opens a stock dossier with MA overlays and score factors.
5. Watchlist add opens an editor; saved notes remain editable in Watchlist.
6. Data refresh shows completion metadata.
7. Desktop 1440 x 900, 1536 x 900, and 1920 x 1080 layouts have no horizontal overflow.

- [ ] **Step 3: Record evidence and rerun the final gate**

Update the verification report with actual counts and browser observations, run `git diff --check`, then run `make verify` once more after documentation changes.

Expected: no whitespace errors and all gates pass on the final commit candidate.
